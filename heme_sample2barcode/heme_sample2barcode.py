#!/usr/bin/env python

"""
heme_sample2barcode.py

Create sample2barcode.txt file from Excel coversheet for Heme-STAMP.
"""

import os
import sys
import openpyxl
import re
import traceback
import wx
import wx.richtext 
from collections import defaultdict
from argparse import ArgumentParser

PROGRAM=os.path.basename(__file__)
VERSION="1.1"
BUILD="180213"

## REVISION HISTORY
# v1.1 180213 - Prepend sample type to front of sample name in sample sheet;
#          Add HEME to control sample name before run number.         
# v1.0 180209 - Initial version.  Label control with _HEME####.  Add 
#          parsing for validation samples.  Control is HD701.

# Validation samples may have one of these SAMPLETYPES followed 
# by '_' prepended to sample name in coversheet
SAMPLETYPES = [ 'PB',   'NormalPB', 
                'BMA',  'NormalBMA',  
                'FFPE', 'NormalFFPE', ]

#----classes------------------------------------------------------------------

class STAMPCoversheet():
    def __init__(self, coversheet, outdir=None, debug=False):
        self.coversheet = coversheet
        self.runnum = None
        self.fields = None
        self.data = []
        self.outdir = None
        self.outfile = None
        self.debug = debug

        try:
            self._parse_coversheet()
            self.get_output_filename(outdir)
        except Exception as e:
            traceback.print_exc()

    def _parse_coversheet(self):
        stamprun_patt = re.compile(
            r'(?:heme|stamp)\s*[id:\s]*[\s_]*(\d+)([a-z]*)[\s_]*\b', flags=re.I)
        wb = openpyxl.load_workbook(self.coversheet, read_only=True)
        wx = wb.active
        for row in wx.iter_rows():
            cells = [ cell.value for cell in row ]
            while cells and cells[-1]==None:
                cells.pop() # remove trailing blanks
            if self.fields and cells:
                # data lines have both Name and barcode fields
                d = dict(zip(self.fields, cells))
                if d.get('Name') and d.get('barcode'):
                    self.data.append(d)
            elif 'Name' in cells and 'lab#' in cells and 'mrn#' in cells:
                # column names
                self.fields = cells
            else: 
                # possible header line with run# info
                line = "\t".join([str(c) for c in cells]) + "\n"
                m = stamprun_patt.search(line)
                if m:
                    self.runnum = "{:04d}".format(int(m.group(1)))
                    if m.group(2) and len(m.group(2))<5:
                        self.runnum += m.group(2)

    def format_sample2barcode(self):
        self.sample2barcode = []
        samples_seen = {}
        for d in self.data:
            name = d['Name'].replace(',','_').replace('(','_').replace(')','')
            lab = str(d['lab#']).strip() if d.get('lab#') else ''
            mrn = str(d['mrn#']).strip() if d.get('mrn#') else ''
            barcode = d['barcode'].strip()
            if not mrn.isdigit():
                if mrn: 
                    print "WARNING: MRN not digit '{}'".format(mrn)
                mrn = ''
            # Check if control sample
            ctrl_patt = '(hd701).*{}'.format(self.runnum)
            if re.match(ctrl_patt, name, flags=re.I):
                sample = name
            # add run num to control name if not already present
            elif re.match('hd701', name, flags=re.I):
                sample = "HD701_HEME{}".format(self.runnum)
            # Patient samples should have lab# or mrn#
            elif lab or mrn: 
                # Change name to last name + first initial(s)
                #  * Entry usually Last, First or Last_First
                #  * Research samples usually sample_research, so don't
                #    split into last, first if '_research'
                #  * Validation samples may start with SAMPLETYPE_
#                names = re.split('[_,]+\s*(?!research)', name.replace('-', ''), 1)
                names = re.split('[_,]+\s*(?!research)', name, 1)
                last = names.pop(0)
                sampletype = ''
                if last in SAMPLETYPES:
                    sampletype = last
                    names = re.split('[_,]+\s*(?!research)', name, 2)[1:]
                    last = names.pop(0)
                first = names.pop() if names else ''
                first = re.sub('([A-Z])[a-z]*', r'\1', first)
                name = re.sub('[\s,]+', '', last+first)
                if lab and lab in name: 
                    # if lab entry already in name, don't duplicate
                    lab = ''
                sample = '_'.join([ v.encode('utf-8') for v in (name, lab, mrn)])
                if sampletype:
                    sample = "{}_{}".format(sampletype, sample)
            else:
                sample = name
            # remove spaces and non-standard characters
            # only allow English letters, digits, hyphens and underscores
            #sample = re.sub(r'[\s\.\x9F-\xFF]', '', sample)
            sample = re.sub(r'[^-\w]', '', sample)
            # make sure not to have duplicate names
            if sample in samples_seen:
                samples_seen[sample] += 1
                sample += '-{}'.format(samples_seen[sample])
            samples_seen[sample] = 1
            self.sample2barcode.append("{}\t{}".format(sample, barcode))
            if self.debug:
                print "{:50s}\t{:30s}\t{}".format(sample, name, d['Name'])
                sys.stdout.flush()
        return self.sample2barcode

    def get_output_filename(self, outdir=None):
        if not outdir:
            outdir = os.path.dirname(self.coversheet)
        if self.runnum:
            outfile = "sample2barcode_HEME{}.txt".format(self.runnum)
        else:
            outfile = "sample2barcode.txt"
        self.outdir = outdir
        self.outfile = os.path.join(outdir, outfile)
        return self.outfile

    def write_sample2barcode_file(self, outfile=None):
        if not outfile:
            outfile = self.outfile
        if not self.sample2barcode:
            self.format_sample2barcode()
        with open(outfile, 'w') as ofh:
            ofh.write("\n".join(self.sample2barcode)+"\n")


#----gui.py-------------------------------------------------------------------

class Sample2Barcode_App(wx.App):
    def __init__(self, args, **kwargs):
        self.args = args
        wx.App.__init__(self, kwargs)

    def OnInit(self):
        self.frame = StampFrame(self.args)
        self.frame.Show()
        self.SetTopWindow(self.frame)
        return True

class StampRTC(wx.richtext.RichTextCtrl):
    def __init__(self, parent):
        wx.richtext.RichTextCtrl.__init__(self, parent, -1, "",
                        style=wx.TE_READONLY|wx.TE_MULTILINE|wx.HSCROLL)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.DoNothing)

    def DoNothing(self, event):
        pass

    def AddIntroBlurb(self):
        title = "Heme-STAMP sample2barcode.txt files"
        intro_blurb="This script creates sample2barcode.txt files for"+\
                    " use with the Heme-STAMP analysis software."+\
                    " Input files should be Excel spreadsheets that"+\
                    " are formatted according to the Heme-STAMP coversheet"+\
                    " conventions."
        attr = wx.TextAttr(alignment=wx.TEXT_ALIGNMENT_CENTER)
        attr.SetFlags(wx.wx.TEXT_ALIGNMENT_CENTER)
        intro_items = [ ]
        self.SetMargins(wx.Point(25,20))
        self.BeginFontSize(10)
        self.Newline()
        self.BeginBold()
        self.WriteText(title)
        self.Newline()
        self.EndBold()
        self.WriteText(intro_blurb)
        self.Newline()
        self.BeginSymbolBullet('*', 25, 30)
        for [label, descr] in intro_items:
            self.BeginBold()
            self.WriteText(label)
            self.EndBold()
            self.WriteText(' -- '+descr)
            self.Newline()
        self.EndSymbolBullet()
        self.EndFontSize()
        self.Newline()
        self.BeginFontSize(10)
        self.WriteText("Drop Heme-STAMP coversheets here:")
        self.Newline()
        self.EndFontSize()

class StampFrame(wx.Frame):
    def __init__(self, args):
        self.args = args
        wx.Frame.__init__(self, None, size=(550,500),
                          title="{} v{}".format(PROGRAM, VERSION), )

        panel = wx.Panel(self)
#        label = wx.StaticText(panel, -1, "Drop Heme-STAMP coversheets here:")
#        self.rtc = wx.richtext.RichTextCtrl(panel,-1, "",
#                        style=wx.TE_READONLY|wx.TE_MULTILINE|wx.HSCROLL)
        self.rtc = StampRTC(panel)
        self.rtc.AddIntroBlurb()
        button_quit = wx.Button(panel, -1, "Quit", style=wx.BU_EXACTFIT)
        button_quit.SetToolTip(wx.ToolTip("Quit application"))
        self.Bind(wx.EVT_BUTTON, self.OnCloseMe, button_quit)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)

        sizer = wx.BoxSizer(wx.VERTICAL)
#        sizer.Add(label, 0, wx.ALL, 5)
        sizer.Add(self.rtc, 1, wx.EXPAND|wx.ALL, 5)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.AddStretchSpacer()
        button_sizer.Add(button_quit, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(button_sizer, 0, wx.ALL|wx.EXPAND, 5)
        panel.SetSizer(sizer)

        filedrop = FileDropProcessing(self.rtc, self.args)
        self.rtc.SetDropTarget(filedrop)

    def OnCloseMe(self, event):
        self.Close(True)

    def OnCloseWindow(self, event):
        self.Destroy()
        
class FileDropProcessing(wx.FileDropTarget):
    def __init__(self, window, args):
        wx.FileDropTarget.__init__(self)
        self.window = window
        self.args = args
        self.num_samples = 0
        self.current_pos = 0

    def ScrollWindow(self):
        pos = self.window.GetScrollRange(wx.VERTICAL)
        self.window.Scroll(0, pos)

    def WriteFormattedText(self, boldtext='', normaltext='', bullet=False,
                           newline=True):
        self.window.MoveEnd()
        if self.current_pos:
            self.window.SetCaretPosition(self.current_pos)
        if bullet:
            self.window.BeginSymbolBullet('*', 25, 30)
        if boldtext:
            self.window.BeginBold()
            self.window.WriteText(boldtext)
            self.window.EndBold()
        if normaltext:
            self.window.WriteText(normaltext)
        if newline: 
            self.window.Newline()
        if bullet:
            self.window.EndSymbolBullet()
        self.ScrollWindow()
        self.current_pos = self.window.GetCaretPosition()

    def OnDropFiles(self, x, y, coversheets):
        coversheet_data = []
        num = 0
        for coversheet in coversheets:
            s2bdata = STAMPCoversheet(coversheet, debug=self.args.debug)
            if s2bdata.fields:
                coversheet_data.append(s2bdata)
            else:
                self.WriteFormattedText(normaltext="Not a recognized input file:  {}".\
                    format(os.path.basename(coversheet)))
                sys.stderr.write("  WARNING: Unrecognized format {}\n".format(coversheet))
            num += 1
            label = " {}".format(num) if len(coversheets)>1 else ''
            self.WriteFormattedText("\nCoversheet{}: ".format(label), 
                                    os.path.basename(coversheet))
            sys.stdout.write("\nCoversheet {}\n".format(coversheet))
            formatted_data = s2bdata.format_sample2barcode()
            if not formatted_data:
                self.WriteFormattedText(newline=False,
                    normaltext="No data in {}\n".format(os.path.basename(coversheet)))
                sys.stdout.write("  WARNING: No data {}\n".format(s2bdata.coversheet))
            else:
                self.WriteFormattedText(normaltext="    "+"\n    ".join(formatted_data))
                self.WriteFormattedText(newline=False,
                    normaltext="Writing {}\n".format(s2bdata.outfile))
                sys.stdout.write("  Writing {}\n".format(s2bdata.outfile))
                s2bdata.write_sample2barcode_file()

def run_gui(args):
    app = Sample2Barcode_App(args)
    app.MainLoop()

#-----------------------------------------------------------------------------
if __name__=='__main__':
    descr = "Create sample2barcode.txt file from STAMP cover sheet."
    parser = ArgumentParser(description=descr)
    parser.add_argument("coversheets", nargs="*",
                        help="STAMP excel coversheets")
    parser.add_argument("-o", "--outdir", 
                        help="Directory to save output file(s)")
    parser.add_argument("--debug", default=False, action='store_true',
                        help="Write debugging messages")

    args = parser.parse_args()
    if not args.coversheets:
        run_gui(args)
    else:
        for coversheet in args.coversheets:
            sys.stdout.write("\nCoversheet {}\n".format(coversheet))
            s2bdata = STAMPCoversheet(coversheet, outdir=args.outdir,
                                      debug=args.debug)
            if not s2bdata.fields:
                sys.stderr.write("  WARNING: Unrecognized format {}\n".\
                format(coversheet))
            else:
                formatted_data = s2bdata.format_sample2barcode()
                if not formatted_data:
                    sys.stdout.write("  WARNING: No data {}\n".format(coversheet))
                else:
                    sys.stdout.write("  Writing {}\n".format(s2bdata.outfile))
                    s2bdata.write_sample2barcode_file()


            



