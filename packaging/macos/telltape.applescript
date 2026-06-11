-- A TUI needs a terminal, which a Finder double-click does not provide. This
-- applet's real Mach-O executable (so it notarizes cleanly) opens Terminal and
-- runs the telltape binary bundled alongside it in Contents/Resources.
on run
	set appPath to POSIX path of (path to me)
	set binPath to appPath & "Contents/Resources/telltape"
	tell application "Terminal"
		activate
		do script quoted form of binPath
	end tell
end run
