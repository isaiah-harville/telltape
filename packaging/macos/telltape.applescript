-- A TUI needs a terminal, which a Finder double-click does not provide. This
-- applet's real Mach-O executable (so it notarizes cleanly) opens Terminal and
-- runs the telltape binary bundled alongside it in Contents/Resources.
on run
	set appPath to POSIX path of (path to me)
	set binPath to appPath & "Contents/Resources/telltape"
	set commandText to "cd " & quoted form of appPath & " && " & quoted form of binPath & "; status=$?; if [ $status -ne 0 ]; then printf '\\ntelltape exited with status %s.\\n' $status; printf 'Press Return to close this window.'; read -r reply; fi; exit $status"
	tell application "Terminal"
		activate
		do script commandText
	end tell
end run
