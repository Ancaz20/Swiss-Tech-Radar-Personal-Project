import sqlite3

conn = sqlite3.connect('swiss_tech_radar.db')
print('jobs:', conn.execute('select count(*) from jobs').fetchone()[0])
print('skills:', conn.execute('select count(*) from skills').fetchone()[0])
print('job_skill_links:', conn.execute('select count(*) from job_skills').fetchone()[0])
print('\nTop skills:')
for row in conn.execute('select name, count(*) from skills join job_skills on job_skills.skill_id = skills.id group by skills.id order by count(*) desc, name limit 10'):
    print(row)
print('\nSample jobs:')
for row in conn.execute('select title, company, location from jobs order by id limit 10'):
    print(row)
conn.close()
