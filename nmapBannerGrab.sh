nmap -sS -sV -p $1 -v -n -Pn --script banner $2 -oG$PWD/output/$3/nmap/$1@$2.txt.grep -oN$PWD/output/$3/nmap/$1@$2.txt