import ingest

jobs = ingest.fetch_jobs('junior developer')
print('count', len(jobs))
for job in jobs[:10]:
    text = f"{job.get('title', '')} {job.get('description', '')}"
    print(job.get('title'))
    print('junior?', ingest.looks_like_junior_role(job))
    print('stack?', ingest.matches_stack_focus(text))
    print('---')
