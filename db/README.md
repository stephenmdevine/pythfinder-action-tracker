# Database Setup & Maintenance

## First-Time Setup

Run these two files in order from your terminal (Git Bash or PowerShell):

```bash
mysql -u root -p < db/schema.sql
mysql -u root -p < db/seed.sql
```

You will be prompted for your MySQL root password each time.

Alternatively, open MySQL Workbench, connect to your local instance,
and run each file using File > Open SQL Script.

---

## Making Schema Changes

Never edit schema.sql directly after the database has been created.
Instead, create a new migration file in db/migrations/ using this naming convention:

    v002_add_column_to_items.sql
    v003_rename_wealth_ledger_column.sql

Each migration file should be self-contained. Example:

```sql
USE pathfinder_tracker;
ALTER TABLE items ADD COLUMN is_magical BOOLEAN DEFAULT FALSE;
```

Run it the same way:

```bash
mysql -u root -p < db/migrations/v002_add_column_to_items.sql
```

This keeps a clear, ordered history of every change made to the schema.

---

## Files

| File            | Purpose                                              |
|-----------------|------------------------------------------------------|
| schema.sql      | Creates the database and all tables (run once)       |
| seed.sql        | Populates baseline PF1e reference data (run once)    |
| migrations/     | One file per schema change after initial setup       |
