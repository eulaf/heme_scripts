heme_water_barcode.py
======================

Installation
------------
The ``heme_water_barcode.py`` script was tested with Python 2.7 and requires 
the xlsxwriter, openpyxl, and wx modules.

A windows executable version of the script was created using pyinstaller.
This enables the progam to be run on hospital workstations without installing 
Python and any of the required modules.  

The command to create the executable is::

    pyinstaller heme_water_barcode.py

Running the executable requires all files in the ``dist`` directory.  

Usage
-----
The 'heme_water_barcode.py' script uses the 'barcode_counts.txt' file
created by the STAMP analysis software as input.  If using the GUI, drag
and drop the 'barcode_counts.txt' file into the text window.  Click the
'Update spreadsheets and DB' button to save results.

If using the commandline, the typical command is:

    heme_water_barcode.py -s -x heme_runs/*/demultiplexed/barcode_counts.txt

To see options, use:

    heme_water_barcode.py -h

