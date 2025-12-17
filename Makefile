.PHONY: start stop restart status logs logs-error install uninstall run clean help

SERVICE := com.telegram-git-bot
PLIST := ~/Library/LaunchAgents/$(SERVICE).plist

help:
	@echo "Telegram Git Bot - Service Management"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Service:"
	@echo "  start       Start the bot service"
	@echo "  stop        Stop the bot service"
	@echo "  restart     Restart the bot service"
	@echo "  status      Show service status"
	@echo ""
	@echo "Logs:"
	@echo "  logs        Tail the bot log"
	@echo "  logs-error  Tail the error log"
	@echo ""
	@echo "Setup:"
	@echo "  install     Install and load the launchd service"
	@echo "  uninstall   Unload and remove the launchd service"
	@echo ""
	@echo "Development:"
	@echo "  run         Run bot manually (foreground)"
	@echo "  clean       Remove log files and cache"

start:
	launchctl start $(SERVICE)
	@sleep 1
	@make status

stop:
	launchctl stop $(SERVICE)
	@echo "Service stopped"

restart:
	launchctl stop $(SERVICE)
	@sleep 1
	launchctl start $(SERVICE)
	@sleep 1
	@make status

status:
	@launchctl list | grep $(SERVICE) || echo "Service not loaded"
	@pgrep -f "uv run main.py" > /dev/null && echo "Process: running" || echo "Process: not running"

logs:
	tail -f bot.log

logs-error:
	tail -f bot-error.log

install:
	@echo "Installing launchd service..."
	cp $(SERVICE).plist $(PLIST) 2>/dev/null || cp launchd.plist $(PLIST)
	launchctl bootstrap gui/$$(id -u) $(PLIST)
	@echo "Service installed and loaded"
	@make status

uninstall:
	@echo "Uninstalling launchd service..."
	-launchctl bootout gui/$$(id -u)/$(SERVICE)
	-rm $(PLIST)
	@echo "Service uninstalled"

run:
	uv run main.py

clean:
	rm -f bot.log bot-error.log
	rm -rf __pycache__
	@echo "Cleaned logs and cache"
