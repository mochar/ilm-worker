# 🧠 Ilm

Home-made implementation of incremental reading and writing.

- Based on Markdown files (Obsidian)
- Server side updating for multi-client support
- Zotero integration
- Complicated, fragile, and ambitious!

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
