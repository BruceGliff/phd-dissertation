#!/bin/bash

for x in autogen-colored/*; do

name_without_ext=$(basename "$x")
name_without_ext="${name_without_ext%.*}"

echo "\\begin{figure}[ht]"
echo "\\centerfloat{\\input{Dissertation/images/exp/$x}}"
echo "\\caption{$name_without_ext}"
echo "\\label{fig:$name_without_ext}"
echo "\\end{figure}"

done

