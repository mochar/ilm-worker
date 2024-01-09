# 🧠 Ilm

Home-made implementation of incremental reading and writing.

- Based on Markdown files (Obsidian)
- Server side updating for multi-client support
- Zotero integration
- Complicated, fragile, and ambitious!

### Workflow

#### Adding items to the system
- Save a page using [Markdownload](https://github.com/deathau/markdownload) with an empty "ilm" property in the frontmatter
  - Optionally, the review date, item score, and other properties can already be given
  - The system will identify this note, give it an id, add any missing properties, and track it
- OR: Save an item in Zotero with the "ilm" property
  - A markdown note will be made for this item
  - Title in the "aliases" property
  - Link to Zotero in the "source" property
 
#### Tracking the items
[Obsidian dataview](https://github.com/blacksmithgu/obsidian-dataview) to present the queue for today:
```
dataview
TABLE WITHOUT ID 
link(file.link, aliases[0]) as "Ilm", 
score as "Score", 
priority as "Priority", 
review as "Review", 
choice(reviewed, "✅", "✘") as "R"
WHERE ilm AND striptime(review) = striptime(date(now))
```

#### Processing an item
- [Obsidian note refactor plugin](https://github.com/lynchjames/note-refactor-obsidian) to extract text to a new note.
- Use the following template to add ilm frontmatter so it can be tracked:
```
---
ilm:
review: 
reviewed: false
parent: "{{link}}"
---

{{new_note_content}}
```
- Use the following template to link to extract. It is wrapped with headers to make it collapsable.
```
###### {{new_note_title}}
!{{new_note_link}}
######
```
- The same plugin can be used to auto-extract into multiple files based on headings

### Setup

- Set up PostgreSQL and create a database named `ilm`
- Fill in and copy `config.example.json` to `$HOME/.config/ilm/config.json`
- Create tables in database `python cli.py create`

Run `index.py` and `process.py` at frequent interval, and `update.py` once a day at midnight. We can achieve this with cron. Run `crontab -e` and add:
```
# Every 20th minute
*/20 * * * * /path/to/python /path/to/ilm-worker/index.py >> /path/to/logs/cron-index.log 2>&1
*/20 * * * * /path/to/python /path/to/ilm-worker/process.py >> /path/to/logs/cron-process.log 2>&1
# At midnight every day
0 0 * * * /path/to/python /path/to/ilm-worker/update.py >> /path/to/logs/cron-update.log 2>&1
```

The Zotero listener is a continuous program that connects to the Zotero server with an active websocket. We can use systemd for this:
- Fill in and copy `ilm-zotero.service` to `$HOME/.config/systemd/user/ilm-zotero.service`
- Ensure will start after reboot: `systemctl --user enable ilm-zotero`
- Start now `systemctl --user start ilm-zotero`
- Log: `journalctl --user -u ilm-zotero`

You may also add it to cron in case something goes wrong with the websocket connection. The `--once` flag runs the script once.
```
*/20 * * * * /path/to/python /path/to/ilm-worker/listen-zotero.py --once >> /path/to/logs/cron-zotero.log 2>&1
```
