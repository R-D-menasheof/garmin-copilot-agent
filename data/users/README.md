# Per-user local staging (`data/users/`)

Owner-operated local workspace for **cloud users** — people (other than the
owner) who use the Vitalis mobile app. The authoritative data for each user
lives in Azure Blob Storage under `users/<oid>/`; this directory is a local
staging area the owner's agent uses to import documents, extract lab data, and
keep local copies of generated reports.

## Layout (per user)

```
data/users/<user-id>/
├── README.md            # who this user is (name, oid, email) — local only
├── incoming/            # drop raw files here (medical PDFs, images) for extraction
├── medical/
│   ├── uploads/         # docs downloaded from the user's cloud area
│   └── extracted/       # structured data extracted by the agent (lab values, JSON)
└── reports/             # local copies of the user's Hebrew health reports
```

`<user-id>` is the user's Entra object id (oid). It matches the cloud path
`users/<oid>/` and the `--user-id` argument of the owner scripts
(`scripts/read_user_data.py`, `scripts/extract_uploaded_medical.py`).

## Privacy

Everything under `data/users/` is **gitignored** (personal health data). Only
this `README.md` and `.gitkeep` are tracked. Never commit a user's files.
