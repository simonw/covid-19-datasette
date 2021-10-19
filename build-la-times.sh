#!/bin/bash
cd california-coronavirus-data
ls *.csv | while read filename;
  do sqlite-utils insert ../la-times.db "${filename%.csv}" $filename --csv -d --alter
done;
