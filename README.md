## Introduction

This is just a simple program that after proper configuration will print out a 
list of transactions and plot a figure of cumulative spending.

The main file is spending_report.py and runs from command line like so:

    spending_report.py 
       Required: 
                --institution <financial institution nickname>
       Optional
                --trend_file <a filename/path to save image>
                --ofx_file <an xml formatted ofx file>
                --start <date in mm/dd/yyyy>
                --end <date in mm/dd/yyyy>
                --config <path to ofxget config file>
                --goal <a spending amount for the week>

# Dependencies

ofxtools
matplotlib
bs4
keyring
numpy

## Configuring ofxget, and password storage

# Install & Configure ofxget 

Configuring ofxget is pretty well documented here (ofxtools doc)[https://ofxtools.readthedocs.io/en/latest/installation.html]

Here are two simple curl scripts to post and get info from an ofx server
be sure to modify the header for your use.
curl_get_sample.sh 
curl_post_sample.sh  

An example of the xml config you will be dealing with
ofx_chase_sample.xml  

If you have trouble installing ofxget see my specific instructions for chase 
& Citi credit cards. Even if you do not have accounts at those institutions 
they can provide some relavent details.

Once installed and configured properly in ~/.config/ofxtools/ofxget.cfg
You can run

    $ ofxget stmt <institution nickname>

typically prompts for password. Enter it and you will get an xml response of
ofx data.

# Configure Password

We can store the password with keyring  
    $ pip install keyring  
    $ pip install keyrings.alt
note: '.alt' only necessary for WSL, which is my setup  
then run:  
    $ ofxget stmt <bank/cc name> --savepass
will store the entered password  

    rerunning --savepass will store a new password

## Example of Authorizing accounts
Because the documentation is not super great, here are the simple steps for adding Citi Credit Card accounts, and chase credit card accounts.
I authorized 3 accounts, and the process was different each time.
I configured Citi credit card, chase credit card, and wells fargo bank.
Wells fargo bank charges a few bucks a month for the ofxget access. So proceed at your discretion

*Caveat: They are subject to change at anytime.*

**For Citi CC**

1. login online
2. click Profile
3. click More Settings
4. under Security click Manage desktop apps
5. click Add access
6. a timer will start (10 mins)
7. add this to ~/.config/ofxtools/ofxget.cfg

        [citi]
        FID = 24909
        ORG = Citigroup
        URL = https://mobilesoa.citi.com/CitiOFXInterface
        user = <user name>
        clientuid = <uuid you generated>
        creditcard = <cc number>
        appid = QWIN
        appver = 2500
        version = 103

8. make a stmt request

        $ ofxget stmt citi
    voila!

9. you will see that an app has been added, mine says Quicken.


**For Chase CC**

1. login online
2. click the Main menu (three horizontal bars icon)
3. click Profile & Settings
4. click AccountSafe^tm
5. click Desktop software
6. click Set up/enable
7. follow simple wizard
8. make ofx.chase.com POST using curl
9. Response


        <OFX>
          ...
            <MESSAGE>
              Please verify your identity within the next 7 days.
              Using your desktop computer, go to your bank's website
              and visit the Secure Message Center for instructions.
        ...
        </OFX>

10. wait < 5 mins
11. login online
12. click Main menu
13. click Secure messages
14. click the message with subject "Action Required for Quicken or QuickBooks users"
15. click "confirm your identity now" & follow short wizard
16. add this to ~/.config/ofxtools/ofxget.cfg

        [chase]
        clientuid = <uuid you generated>
        user = <username>
        creditcard = <cc number>
        appver = 2700
        version = 220

17. make a stmt request

        $ ofxget stmt chase
    voila!

