- Create dir `$HOME/.local/share/ilm`
- `python cli.py create`


- Set `$HOME/.config/ilm/config`
- Copy `ilm-zotero.service` to `/home/mochar/.config/systemd/user/ilm-zotero.service`
- Ensure will start after reboot: `systemctl --user enable ilm-zotero`
- Start now `systemctl --user start ilm-zotero`
- Log: `journalctl --user -u ilm-zotero`
