from pathlib import Path
import pandas as pd

csv_path = Path('job_report.csv')
excel_path = Path('job_report.xls')

df = pd.read_csv(csv_path)
df.to_excel(excel_path, index=False, engine='openpyxl')
print(excel_path)
