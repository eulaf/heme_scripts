## Scripts to determine expected variants

./heme_parse_exome_data.py Heme-STAMP_APR2018.bed docs/2016-01-13_*.txt > exome_variants_in_hemeROI.txt

./heme_compare_hd701.py -o HD701_S5_exomeCheck_Output_Mutation_Report1_annovar_categorized.txt -t HD701_truths.txt docs/HD701_S5_Output_Mutation_Report1_annovar_categorized.txt exome_variants_in_ROI.txt



## Horizon online info
## https://www.horizondiscovery.com/reference-standards/quantitative-multiplex-reference-standard-hd701
## https://www.horizondiscovery.com/resources/support-materials/data?d_cat=reference-standards
## https://www.horizondiscovery.com/resources/scientific-literature/faq/cfdna#a13

# Run on all control files and merge results
for f in ../testfiles/heme_hd701/HD701_*txt; do 
    y=${f/.*_00/00}; 
    y=${y/.*_HEME/};
    y=${y/.var*/}; 
    echo $y $f; 
    ./heme_compare_hd701.py -o output/HD701_truths_${y}.txt -t output/truths_HD701_heme${y}.txt $f exome_variants_in_hemeROI.txt; 
done
cat output/truths_HD701_heme* | /bin/sort -u | /bin/sort -k11,11 -k1,1 -k3,3n > truths_HD701.txt
# manually edit file
# manually delete line with PIK3CA	chr3	178936091	E545K	YES	Verified - 9.0%	3

