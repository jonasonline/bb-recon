#Input ffuf folder and general output folder
ls $1/*.incremental.txt | xargs -I{} cat {} > $2/incrementalContent.txt
sort -u $2/incrementalContent.txt -o $2/incrementalContent.txt