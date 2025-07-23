import openpyxl

workbook = openpyxl.load_workbook('/home/doughnut/github/unimelb-phd-phase-1/data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm')
print(workbook.sheetnames)