#!/usr/bin/env python

"""
heme_compare_hd701.py -- compare hd701 heme panel results against 
expected mutations in exome data

"""

import os
import re
import string
import sys
from collections import defaultdict
from argparse import ArgumentParser

VERSION="0.1"
BUILD="180424"

#----constants----------------------------------------------------------------

POS_FIELD = 'Position (GRCh37)'
VAF_FIELD = '"Expected Allelic Frequency, %"'

#----common functions---------------------------------------------------------

def getScriptPath():
  return os.path.dirname(os.path.realpath(sys.argv[0]))

def is_float(v):
  try:
    float(v)
  except ValueError:
    return False
  return True

def convert_type(v):
  if v.isdigit():
    return int(v)
  elif is_float(v):
    return float(v)
  else:
    return v

def convert_types(vlist):
  return [ convert_type(v) for v in vlist ]

#---- classes ----------------------------------------------------------------

class BEDFile:
  def __init__(self, bedfile=None):
    self.bedfile = bedfile
    self.fields = ['chrom','start','end','comment']
    self.rows = []
    self.data = defaultdict(dict)
    self.num_regions = 0
    self._parse_bed_file()

  def _parse_bed_file(self):
    with open(self.bedfile, 'r') as fh:
      for line in fh:
        vals = line.rstrip('\n\r').split("\t")
        if any(v for v in vals): # not empty line
          d = dict(zip(self.fields, vals))
          d['line'] = line
          d['start'] = int(d['start'])
          d['end'] = int(d['end'])
          self.rows.append(d)
          self.data[d['chrom']][d['start']] = d
    self.num_regions = len(self.rows)
    sys.stderr.write("  BED file: {} regions\n".format(self.num_regions))
    sys.stderr.flush()

  def in_roi(self, chrom, pos):
    inROI = False
    if chrom in self.data:
      for start, d in sorted(self.data[chrom].items()):
        if pos >= start and pos <= d['end']: 
          inROI = True
        elif pos < start:
          break
    return inROI


  def outfile_name(self, outdir=None, outext='', inext='.txt'):
    outfile = self.report.replace(inext, '') 
    if outext:
      outfile += outext
    if outdir:
      outfile = os.path.join(outdir, os.path.basename(outfile))
    self.outfile = outfile
    return outfile

class ExomeData:
  required_cols = ['Gene', 'Chromosome', POS_FIELD, 'Ref.', 'Alt.', 'Type',
                   'HGVS DNA change', 'HGVS AA change']

  def __init__(self, exomefiles=[], debug=False):
    self.files = exomefiles
    self.data = defaultdict(lambda: defaultdict(list))
    self.rows = {}
    self.fields = []
    self.missing_fields = []
    self.header = []
    self.debug = debug
    for f in self.files:
      self._parse_data_file(f)

  def _check_for_required_fields(self, fields):
    for col in self.required_cols:
      if not col in fields:
        self.missing_fields.append(col)
    return self.missing_fields

  def _parse_data_file(self, filename):
    if self.debug:
      print "Parsing "+filename
    fields = None
    self.rows[filename] = []
    with open(filename, 'r') as fh:
      for line in fh:
        if fields: # already have fields so data lines follow
          vals = line.rstrip("\n\r").split("\t")
          if any(v for v in vals): # not empty line
            d = dict(zip(fields, vals))
            d['line'] = line
            d['filename'] = filename
            if d[POS_FIELD].isdigit():
              d[POS_FIELD] = int(d[POS_FIELD])
              pos = d[POS_FIELD]
              if d['Type'] in ('DEL','INS'):
                pos += 1
              self.rows[filename].append(d)
              self.data[d['Chromosome']][pos].append(d)
            else:
              sys.stderr.write("LINE: "+ line)
        else:
          if self.required_cols[-1] in line: # field list
            fields = line.rstrip().split('\t')
            sys.stderr.write(",".join(fields)+";\n")
            self._check_for_required_fields(fields)
            for f in fields: # self.fields is union of all fields in files
              if f not in self.fields:
                self.fields.append(f)
          else:
            self.header.append(line)
    sys.stderr.write("  {}: {} rows of data parsed\n".format(filename, 
                     len(self.rows[filename])))
    sys.stderr.flush()
    return len(self.rows[filename])

class ReportData:
  required_cols = ['Gene', 'Chr', 'Position', 'Ref Transcript',
                   'Ref', 'Var', 'CDS Change', 'AA Change', 'Whitelist']

  def __init__(self, report=None):
    self.report = report
    self.fields = []
    self.missing_fields = []
    self.header = []
    self.data = []
    self.num_variants = 0
    self.outfile = None
    if report.endswith('.txt'):
      self._parse_variant_report()
    else:
      self._parse_variant_report_spreadsheet()

  def _check_for_required_fields(self, fields):
    for col in self.required_cols:
      if not col in fields:
        sys.stderr.write("  missing {}\n".format(col))
        self.missing_fields.append(col)
    return self.missing_fields

  def _parse_variant_report(self):
    with open(self.report, 'r') as fh:
      for line in fh:
        if not self.fields: # in header
          if self.required_cols[0] in line: # field list
            self.fields = line.rstrip().split("\t")
            self._check_for_required_fields(self.fields)
          else:
            self.header.append(line)
        else: # data
          vals = line.rstrip('\n\r').split("\t")
          if any(v for v in vals): # not empty line
            d = dict(zip(self.fields, vals))
            d['line'] = line
            self.data.append(d)
    self.num_variants = len(self.data)

  def _parse_variant_report_spreadsheet(self):
    wb = openpyxl.load_workbook(self.report, read_only=True)
    ws = wb.active
    for row in ws.iter_rows():
      cells = [ cell.value for cell in row ]
      while cells and cells[-1]==None: 
        cells.pop()# remove trailing blanks
      line = "\t".join([str(c) for c in cells])+"\n"
#      sys.stderr.write(line)
      if not self.fields: # in header
        if self.required_cols[0] in cells: # field list
          self.fields = cells
          self._check_for_required_fields(self.fields)
        else:
          self.header.append(line)
      else: # data
        if any(v for v in cells): # not empty line
          d = dict(zip(self.fields, cells))
          d['line'] = line
          self.data.append(d)
    self.num_variants = len(self.data)
    wb._archive.close()

  def outfile_name(self, outdir=None, outext='', inext='.txt'):
    outfile = self.report.replace(inext, '') 
    if outext:
      outfile += outext
    if outdir:
      outfile = os.path.join(outdir, os.path.basename(outfile))
    self.outfile = outfile
    return outfile

#-----------------------------------------------------------------------------

def pos_sortkey(chrom, pos):
  chrom = "%02d" % int(chrom) if (type(chrom)==int or chrom.isdigit()) else "%-2s" % chrom
  return "%s.%011d" % (chrom, pos)

def chrom_sortkey(chrom):
  chrom = chrom.replace('chr','')
  chrom = "%02d" % int(chrom) if (type(chrom)==int or chrom.isdigit()) else "%-2s" % chrom
  return chrom

#-----------------------------------------------------------------------------

def create_annotated_variant_report(ofh, reportdata, exomedata):
  fields = reportdata.fields[:] + ['Horizon',]
  ofh.write("\t".join(fields)+"\n")
  for d in reportdata.data:
    chrom = d['Chr']
    pos = int(d['Position'])
    d['Horizon'] = ''
    if chrom in exomedata.data and pos in exomedata.data[chrom]:
      exomerows = exomedata.data[chrom][pos]
      d['Horizon'] = "IN_EXOME"
      for e in exomerows:
        if 'Variant' in e and e['Variant']:
          d['Horizon'] = 'VERIFIED - '+e['Variant']
          if VAF_FIELD in e:
            d['Horizon'] += ', '+e[VAF_FIELD]+'%'
          else:
            sys.stderr.write("no vaf field: {}\n".format(d))
          break
    vals = [ str(d[f]) for f in fields ]
    ofh.write("\t".join(vals)+"\n")

def create_truthfile(ofh, reportdata, exomedata):
  mapfields = { # variant report field => db field
    'Gene': 'gene',
    'Chr': 'chr',
    'Position': 'position',
    'Ref Transcript': 'ref_transcript', 
    'Ref': 'ref',
    'Var': 'var',
    'CDS Change': 'HGVS',
    'AA Change': 'protein', 
    'Whitelist': 'whitelist', 
    'Horizon': 'horizon', 
    'Artifact?': 'artifact', 
  }
  fields = reportdata.required_cols[:] + ['Horizon', 'is_expected']
  if 'Artifact?' in reportdata.fields:
    fields.append('Artifact?')
  ofh.write("\t".join([ mapfields[f] if f in mapfields else f \
            for f in fields])+'\n')
  for d in reportdata.data:
    chrom = d['Chr']
    pos = int(d['Position'])
    if chrom in exomedata.data and pos in exomedata.data[chrom]:
      exomerows = exomedata.data[chrom][pos]
      d['Horizon'] = "confirmed in parental cell line"
      d['is_expected'] = 2
      for e in exomerows:
        if 'Variant' in e and e['Variant']:
          d['Horizon'] = 'Verified'#+e['Variant']
          d['is_expected'] = 3
          if VAF_FIELD in e:
            d['Horizon'] += ' - '+e[VAF_FIELD]+'%'
          else:
            sys.stderr.write("no vaf field: {}\n".format(d))
          break
  for d in sorted(reportdata.data, key=lambda d: "{}:{:20}:{:09d}".format(\
                  9-d.get('is_expected', 0), d['Gene'], int(d['Position']))):
    vals = [ str(d.get(f,'')) for f in fields ]
    ofh.write("\t".join(vals)+'\n')

#-----------------------------------------------------------------------------
if __name__=='__main__':
  descr = "Compare panel results to variants in exome data"
  parser = ArgumentParser(description=descr)
  parser.add_argument("report", help="HD701 mutation report")
  parser.add_argument("exomefiles", nargs="+", help="Exome data file(s)")
  parser.add_argument("-t", "--truthfile", help="Create truth file")
  parser.add_argument("-o", "--outfile", 
                      help="Create annotated mutation report file")
  parser.add_argument("--debug", default=False, action='store_true',
                      help="Write debugging messages")

  if len(sys.argv)<3:
    parser.print_help()
    sys.exit()
  args = parser.parse_args()
  reportdata = ReportData(args.report)
  exomedata = ExomeData(args.exomefiles, debug=args.debug)

  if args.outfile:
    with open(args.outfile, 'w') as ofh:
      sys.stderr.write("  Writing {}\n".format(args.outfile))
      create_annotated_variant_report(ofh, reportdata, exomedata)
  if args.truthfile:
    with open(args.truthfile, 'w') as ofh:
      sys.stderr.write("  Writing {}\n".format(args.truthfile))
      create_truthfile(ofh, reportdata, exomedata)

