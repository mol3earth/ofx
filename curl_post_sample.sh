#! /bin/sh
curl -X POST \
	-H "Content-Type:application/x-ofx" \
	-H "OFXHEADER:100" \
	-H "DATA:OFXSGML" \
	-H "VERSION:102" \
	-H "SECURITY:NONE" \
       	-H "ENCODING:USASCII" \
	-H "CHARSET:1252" \
	-H "COMPRESSION:NONE" \
	-H "OLDFILEUID:NONE" \
	-H "NEWFILEUID:86c1b52b-8e3d-4b26-9b1b-addf11b6cec2"  \
	-d @ofx_chase.xml \
	https://ofx.chase.com
