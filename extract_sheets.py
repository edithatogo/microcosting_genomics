import openpyxl
import csv

workbook = openpyxl.load_workbook('/home/doughnut/github/unimelb-phd-phase_1/data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm')

sheets_to_export = ['At a Glance', 'Summary Table', 'Detailed Table', 'Process', 'Labour - Costs - VCGS', 'Cons -  Costs and Util - VCGS', 'Eq - Costs and Usage - VCGS']

for sheet_name in sheets_to_export:
    sheet = workbook[sheet_name]
    with open(f'/home/doughnut/github/unimelb-phd-phase_1/data/{sheet_name}.csv', 'w', newline="") as f:
        c = csv.writer(f)
        for r in sheet.rows:
            c.writerow([cell.value for cell in r])
