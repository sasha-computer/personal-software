Output assets/domain-search-demo.gif

Set Shell "fish"
Set Width 1140
Set Height 700
Set FontSize 22
Set FontFamily "Berkeley Mono Variable"
Set Padding 24
Set Theme "Catppuccin Frappe"
Set TypingSpeed 35ms
Set Framerate 30

Type "clear"
Enter
Sleep 700ms

Type "uvx domain-search creative --tld com io dev --output demo.json"
Enter
Sleep 5s

Type "uvx domain-search --hack creative --output creative-hacks.json"
Enter
Sleep 5s

Type "jq . creative-hacks.json"
Enter
Sleep 7s
