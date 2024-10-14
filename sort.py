#!/usr/bin/env python3
# Read the file
with open('list.txt', 'r') as file:
    lines = [line for line in file if line.strip()]

# Sort lines first by the first column and then by the second column
sorted_lines = sorted(lines, key=lambda x: (x.split()[0], x.split()[1]))

# Write the sorted lines back to the file or print them
with open('list.txt', 'w') as file:
    file.writelines(sorted_lines)

