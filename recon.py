import json, os, subprocess, shutil, requests, argparse, datetime

parser = argparse.ArgumentParser(description='Doing recon.')
parser.add_argument('--program', help="Specify a program name ju run that program only.")
parser.add_argument('--nodomainrecon', action='store_const', const=True, help="Skip looking for new sub domains")
parser.add_argument('--noportscan', action='store_const', const=True, help="Skip port scan")
parser.add_argument('--nobanner', action='store_const', const=True, help="Skip banner grabing")
parser.add_argument('--noslack', action='store_const', const=True, help="Skip posting to Slack")
parser.add_argument('--nohttp', action='store_const', const=True, help="Skip http discovery")
parser.add_argument('--nocontent', action='store_const', const=True, help="Skip content discovery")
args = parser.parse_args()


def postToSlack(webhookURL, message):
    requests.post(webhookURL, json={"text":message})
def myconverter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()

with open('config.json', 'r') as configFile:
    config = json.load(configFile)

with open('programs.json') as programsFile:
    programs = json.load(programsFile)
    for program in programs['programs']:
        if program['enabled'] == False:
            continue
        if args.program and program['programName'] != args.program:
            continue
        
        firstRun = True
        uniqueDomains = set([])
        programName = program['programName']
        amassFolder = './output/' + programName + '/amass'
        subfinderFolder = './output/' + programName + '/subfinder'
        masscanFolder = './output/' + programName + '/masscan'
        digFolder = './output/' + programName + '/dig'
        gobusterFolder = './output/' + programName + '/gobuster'
        nmapFolder = './output/' + programName + '/nmap'
        ffufFolder = './output/' + programName + '/ffuf'
        os.makedirs(amassFolder, exist_ok=True, )
        os.makedirs(subfinderFolder, exist_ok=True, )
        os.makedirs(masscanFolder, exist_ok=True, )
        os.makedirs(digFolder, exist_ok=True, )
        os.makedirs(gobusterFolder, exist_ok=True, )
                    
        for target in program['scope']:
            if target['inScope'] == True:
                if 'url' in target:
                    print(target['url'] + ': No URL Processing implemented.')
                elif 'domain' in target:
                    domainBase = target['domain'].replace('*.','')
                    
                    #Saving old files for comparison 
                    amassDomainFolder = amassFolder + "/" + domainBase
                    if os.path.isdir(amassDomainFolder):
                        for filename in os.listdir(amassDomainFolder):
                            if not filename.endswith('.old'):
                                shutil.copy(amassDomainFolder + '/' + filename, amassDomainFolder + '/' + filename + '.old')

                    #run amass
                    amassArguments = '-active -d ' + domainBase + ' -dir ./output/' + programName + '/amass/' + domainBase + '/'
                    print(amassArguments)
                    if args.nodomainrecon == None:
                        subprocess.run('amass enum ' + amassArguments, shell=True)

                    #run subfinder
                    subfinderOutputFolder = './output/' + programName + '/subfinder/'
                    if not os.path.exists(subfinderOutputFolder):
                        os.makedirs(subfinderOutputFolder)
                    subfinderArguments = '-d ' + domainBase + ' -o ./output/' + programName + '/subfinder/' + domainBase + '.json -oJ -t 10 -v -b -w ./wordlists/subdomains/jhaddix_all.txt -r 1.1.1.1, 8.8.8.8' 
                    #print(subfinderArguments)
                    if args.nodomainrecon == None:
                        subprocess.run('~/go/bin/subfinder ' + subfinderArguments, shell=True)

                    #Processing unique names
                    #Amass unique names
                    for filename in os.listdir(amassDomainFolder):
                        if filename.endswith('.json') and not filename.endswith('_data.json'):
                            with open(amassDomainFolder + '/' + filename) as amassOut:
                                for line in amassOut:
                                    try:    
                                        output = json.loads(line)
                                        uniqueDomains.add(output['name'])
                                    except:
                                        print('Error')
                    #Subfinder unique names
                    for filename in os.listdir(subfinderOutputFolder):
                        if filename.endswith('.json'):
                            with open(subfinderOutputFolder + '/' + filename) as subfinderOut:
                                output = json.load(subfinderOut)
                                for domain in output:    
                                    try:    
                                        sanitizedDomain = domain.lstrip('.')
                                        uniqueDomains.add(sanitizedDomain)        
                                    except:
                                        print('Error')
                    

        #compare old and new current domains
        if os.path.isfile('./output/' + programName + '/sortedDomains.json'):
            firstRun = False
            shutil.copy('./output/' + programName + '/sortedDomains.json', './output/' + programName + '/sortedDomains.json.old')
        with open('./output/' + programName + '/sortedDomains.json', 'w') as f:
            json.dump(sorted(uniqueDomains), f)
        if os.path.isfile('./output/' + programName + '/sortedDomains.json.old'):
            with open('./output/' + programName + '/sortedDomains.json', 'r') as current:
                currentData = json.load(current)
                currentDataSet = set(currentData)
                with open('./output/' + programName + '/sortedDomains.json.old', 'r') as old:
                    oldData = json.load(old)
                    oldDataSet = set(oldData)
                    for domain in currentDataSet:
                        if domain not in oldDataSet and firstRun == False and args.noslack == None:
                            message = 'New domain for ' + programName + ': ' + domain
                            print(message)
                            postToSlack(config["slackWebhookURL"], message)
            
        #add domains to incremental domain list
        with open('./output/' + programName + '/sortedDomains.json', 'r') as current:
            currentData = json.load(current)
            currentDataSet = set(currentData)
            with open('./output/' + programName + '/incrementalDomains.txt', 'a+') as inc:
                inc.seek(0)
                incDomains = set(line.strip() for line in inc)
                for domain in currentDataSet:
                    if domain not in incDomains:
                        print('Adding domain ' + domain + ' to incremental list for ' + programName)
                        inc.write("%s\n" % domain)

        #add domains to incremental content domain list
        contentDomainsFilePath = './output/' + programName + '/contentDomains.json'
        if not os.path.exists(contentDomainsFilePath):
            with open(contentDomainsFilePath, 'w+') as contentDomains:
                print('Created file: ' + contentDomainsFilePath)
        with open(contentDomainsFilePath, 'r') as contentDomains:
            contentDomains.seek(0)
            if contentDomains.read(1):
                contentDomains.seek(0)    
                incrementalContentDomains = json.load(contentDomains)
            else:
                incrementalContentDomains = {}
        with open('./output/' + programName + '/incrementalDomains.txt', 'r') as inc:
            inc.seek(0)
            incDomains = set(line.strip() for line in inc)
            for domain in incDomains:
                if domain not in incrementalContentDomains:
                    incrementalContentDomains[domain] = {"Added": datetime.datetime.now(), "Status": "Pending"}
            with open('./output/' + programName + '/contentDomains.json', 'w') as contentDomains:
                json.dump(incrementalContentDomains, contentDomains, default = myconverter)

        #port scan domains
        if args.noportscan == None:
            with open('./output/' + programName + '/incrementalDomains.txt', 'r') as domains:
                domains.seek(0)
                for domain in domains:
                    scriptArguments = domain.rstrip() + '' + programName
                    subprocess.run('sudo ./digAndMasscan.sh ' + scriptArguments, shell=True)
        #BanerGrabbing
        if args.nobanner == None:
            scannedDomains = set([])
            if os.path.isdir(masscanFolder):
                for filename in os.listdir(masscanFolder):
                    currentDomain = filename.split("@")[0]
                    if currentDomain not in scannedDomains:
                        print(currentDomain)
                        with open(filename, 'r') as masscanOutFile:
                            masscanOut = json.load(masscanOutFile)
                            print(masscanOut)
                            print('Not implemented')
                            #scriptArguments = 
                            #subprocess.run('sudo ./nmapBannerGrab.sh ' + scriptArguments, shell=True)
                            #scannedDomains.add(currentDomain)

        #Content discovery
        with open('./output/' + programName + '/contentDomains.json', 'r') as domains:
            domains.seek(0)
            contentDomains = json.load(domains)
            for domain in contentDomains:
                if args.nohttp == None and args.nocontent == None:
                    urlHttp = "http://" + domain
                    #TODO
                    #subprocess.run('ffuf ' + scriptArguments, shell=True)
                if args.nocontent == None:
                    if 'Status' in contentDomains[domain]:
                        if contentDomains[domain]['Status'] == 'Enabled':
                            urlHttps = "https://" + domain
                            outfileHttps = './output/' + programName + '/ffuf/https@' + domain + '.json'
                            outfileHttpsIncremental = './output/' + programName + '/ffuf/https@' + domain + '.incremental.txt'
                            """ if os.path.exists(outfileHttps):
                                shutil.copyfile(outfileHttps, outfileHttps + '.prev.json') """
                            scriptArguments = ' -t 100 -timeout 3 -r -w '
                            if 'ContentScanLevel' in contentDomains[domain]:
                                if contentDomains[domain]['ContentScanLevel'] == 'Full':
                                    scriptArguments += 'wordlists/directories/content_discovery_nullenc0de.txt '
                            else:
                                    scriptArguments += 'lib/SecLists/Discovery/Web-Content/SVNDigger/all.txt '
                            scriptArguments += '-u ' + urlHttps + '/FUZZ -o ' + outfileHttps + ' '
                            if 'FilterSize' in contentDomains[domain]:
                                scriptArguments += ' -fs ' + contentDomains[domain]['FilterSize']
                            if 'RequestDelay' in contentDomains[domain]:
                                scriptArguments += ' -p ' + contentDomains[domain]['RequestDelay']
                            if 'FilterWords' in contentDomains[domain]:
                                scriptArguments += ' -fw ' + contentDomains[domain]['FilterWords']
                            print(scriptArguments)
                            subprocess.run('~/go/bin/ffuf ' + scriptArguments, shell=True)
                            #add https content to incremental content list
                            addedContent = False
                            with open(outfileHttps, 'r') as current:
                                currentData = json.load(current)
                                with open(outfileHttpsIncremental, 'a+') as inc:
                                    inc.seek(0)
                                    incContent = set(line.strip() for line in inc)
                                    if 'results' in currentData:
                                        for content in currentData['results']:
                                            contentURL = urlHttps + '/' + content['input']
                                            if contentURL not in incContent:
                                                print('Adding ' + contentURL + ' to incremental list for ' + urlHttps)
                                                inc.write("%s\n" % contentURL)
                                                addedDomains = True
                            if addedContent and args.noslack == None:
                                message = 'New content for ' + programName + ' domain: ' + domain
                                print(message)
                                postToSlack(config["slackWebhookURL"], message)




                    
                    
                        


                
