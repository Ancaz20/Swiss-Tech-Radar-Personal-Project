from pathlib import Path
import pandas as pd

csv_path = Path('job_report.csv')
xlsx_path = Path('job_report.xlsx')

df = pd.read_csv(csv_path)
df.to_excel(xlsx_path, index=False)
print(xlsx_path)
