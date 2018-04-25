#!/usr/bin/env python

"""
myeloid_parse_exome_data.py -- parse exome data for control and myeloid BED 
file and return variants in BED file regions only

"""

import os
import re
import string
import sys
from collections import defaultdict
from argparse import ArgumentParser

VERSION="0.1"
BUILD="161212"

#----constants----------------------------------------------------------------

POS_FIELD = 'Position (GRCh37)'

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
      sys.stderr.write("Parsing "+filename+'\n')
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
              self.rows[filename].append(d)
              self.data[d['Chromosome']][d[POS_FIELD]].append(d)
            else:
              sys.stderr.write("LINE: "+", ".join(vals)+'\n')
        else:
          if self.required_cols[-1] in line: # field list
            fields = line.rstrip().split('\t')
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



#-----------------------------------------------------------------------------

def pos_sortkey(chrom, pos):
  chrom = "%02d" % int(chrom) if (type(chrom)==int or chrom.isdigit()) else "%-2s" % chrom
  return "%s.%011d" % (chrom, pos)

def chrom_sortkey(chrom):
  chrom = chrom.replace('chr','')
  chrom = "%02d" % int(chrom) if (type(chrom)==int or chrom.isdigit()) else "%-2s" % chrom
  return chrom

#-----------------------------------------------------------------------------
if __name__=='__main__':
  descr = "Take exome data and BED file and return only variants that are in "
  descr += " BED file regions."
  parser = ArgumentParser(description=descr)
  parser.add_argument("bedfile", help="BED file")
  parser.add_argument("exomefiles", nargs="+", help="Exome data file(s)")
  parser.add_argument("-o", "--outdir", 
                      help="Directory to save output file(s)")
  parser.add_argument("--debug", default=False, action='store_true',
                      help="Write debugging messages")

  if len(sys.argv)<3:
    parser.print_help()
    sys.exit()
  args = parser.parse_args()
  roi = BEDFile(args.bedfile)
  exomedata = ExomeData(args.exomefiles, debug=args.debug)
  numrows = 0
#  print "\t".join(exomedata.required_cols)
  print "\t".join(exomedata.fields)
  seen = {}
  for chrom in sorted(exomedata.data.keys(), key=chrom_sortkey):
    posdata = exomedata.data[chrom]
    for pos, rows in sorted(posdata.items()):
      if roi.in_roi(chrom, pos):
        for d in sorted(rows, reverse=True, key=lambda d: 
                       (d.get('Variant',''), d.get('filename',''))):
          vals = [ str(d[f]) if d[f] != None else '' \
                   for f in exomedata.required_cols ]
          ref_alt = "\t".join(vals[0:-2])
          if not ref_alt in seen:
            vals = [ str(d[f]) if f in d else '' \
                   for f in exomedata.fields ]
            sys.stdout.write("\t".join(vals)+"\n")
            numrows += 1
            seen[ref_alt] = True
  sys.stderr.write("{} variants in ROI\n".format(numrows))



