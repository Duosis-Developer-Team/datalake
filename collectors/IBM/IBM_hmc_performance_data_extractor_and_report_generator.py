#!/usr/bin/python3
# Version 4
import hmc_pcm as hmc
import nchart
import time
import sys
import os

if len(sys.argv) != 4:   # four including the program name entry [0]
    print("Usage: %s HMC-hostname HMC-username HMC-password" %(sys.argv[0]))
    sys.exit(1)
hostname=sys.argv[1]
user    =sys.argv[2]
password=sys.argv[3]

print("HMC hostanme=%s User=%s Password=%s"  %( hostname, user, password))

output_csv=True
output_html=False
debug=False
debugDir = "./debug"

if not os.path.exists(debugDir):
	os.makedirs(debugDir)

print("-> Logging on to %s as user %s" % (hostname,user))
hmc = hmc.HMC(hostname, user, password)

print("-> Get Preferences") # returns XML text
prefstripped = hmc.get_stripped_preferences_pcm()
hmc.save_to_file("server_perferences.xml",prefstripped)

print("-> Parse Preferences")
serverlist = hmc.parse_prefs_pcm(prefstripped)  # returns a list of dictionaries one per Server
perflist = []
all_true = True
print("-> ALL servers:")
for num,server in enumerate(serverlist):
    if server['lterm'] == 'true' and server['agg'] == 'true':
        todo = "- OK"
        perflist.append(server)
    else:
        todo = "- remove"
    print('-> Server name=%-16s agg=%-5s longterm=%-5s %s ' 
        %(server['name'], server['agg'], server['lterm'], todo))

print("-> Servers with Perf Stats")
for count, server in enumerate(perflist,start=1):  # just loop the servers with stats
    print('')

    ### Remove hashes from next three lines to explicitly exclude any servers that do not have VIOS running
    ###if server['name'] == 'core-bP8-S814':
    ###    print("Skipping server %s as it has no VIOS" % (server['name']))
    ###    continue

    print('--> Server=%d Getting filenames for %s' %(count,server['name']))
    starttime = time.time()
    filelist = hmc.get_filenames_server(server['atomid'],server['name']) # returns XML of filename(s)
    endtime = time.time()
    print("---> Received %d file(s) in %.2f seconds" % (len(filelist), endtime - starttime))

    for num,file in enumerate(filelist,start=1): # loop around the files
        filename=file['filename']
        url=file['url']
        print('---> Server=%s File=%d %s' %(server['name'], num,filename))


    for num,file in enumerate(filelist,start=1): # loop around the files
        filename=file['filename']
        url=file['url']
        data = hmc.get_stats(url,filename, server['name']) # returns JSON stats

        if filename[:13] == "ManagedSystem": # start of the filename tells you if server or LPAR
            filename2 = filename.replace('.json','.JSON')
            print('\n\nManagedSystem\n---> Save readable JSON File=%d bytes=%d name=%s' %(num,len(data),filename2))
            hmc.save_json_txt_to_file(filename2,data)

            info = hmc.extract_server_info(data)
            print("----> ServerInfo name=%s mtms=%s type=%s frequency=%s seconds\n----> ServerInfo Date=%s start=%s end=%s" %( info['name'], info['mtms'], info['mtype'], info['freq'], info['stime'][:10], info['stime'][11:19], info['etime'][11:19]))

            header, stats, errors, lines = hmc.extract_server_stats(data)
            print("----> Records=%d Errors=%d" % (lines,errors))
            if errors > 0:
                print("Stopping processing of this server %s due to errors"%(info['name']))
                print("This may be due to teh server NOT having any VIOS LPARs.")
                break

            if output_html:                                              # Create .html file that graphs the stats
                filename = "Server-" + info['name'] + str(starttime) + ".html"          # Using googlechart
                n = nchart.nchart_open()
                n.nchart_server(filename, info, stats)
                print("Saved webpage to %s" % (filename))

            if output_csv:                                               # Create comma separated vaules file
                filename = "Server-" + info['name'] + str(starttime) + ".csv"
                f = open(filename,"a")
                f.write("%s\n" %(header))
                for line in stats:
                    f.write("%s, %.2f,%.2f,%.2f,%.2f, %d,%d,%d,%d, %.2f,%.2f,%.2f, %.1f,%.1f, %.1f,%.1f,%.1f,%.1f, %.1f,%.1f,%.1f,%.1f\n" %( line['time'], 
                        line['cpu_avail'], line['cpu_conf'], line['cpu_total'], line['cpu_used'], 
                        line['mem_avail'], line['mem_conf'], line['mem_total'], line['mem_inVM'],
                        line['vios_cpu_vp'], line['vios_cpu_entitled'], line['vios_cpu_used'],
                        line['vios_mem_conf'], line['vios_mem_used'], 
                        line['vios_net_rbytes'], line['vios_net_wbytes'], line['vios_net_reads'], line['vios_net_writes'],
                        line['vios_fc_rbytes'], line['vios_fc_wbytes'], line['vios_fc_reads'], line['vios_fc_writes'] ))
                f.close()
                print("Saved comma separated values to %s" % (filename))

            if debug:
                print("-----> Header=%s" % (header))
                for lines,line in enumerate(stats):
                    print("%s, %.2f,%.2f,%.2f,%.2f, %d,%d,%d,%d, %.2f,%.2f,%.2f, %.1f,%.1f, %.1f,%.1f,%.1f,%.1f, %.1f,%.1f,%.1f,%.1f" %( line['time'], 
                        line['cpu_avail'], line['cpu_conf'], line['cpu_total'], line['cpu_used'], 
                        line['mem_avail'], line['mem_conf'], line['mem_total'], line['mem_inVM'],
                        line['vios_cpu_vp'], line['vios_cpu_entitled'], line['vios_cpu_used'],
                        line['vios_mem_conf'], line['vios_mem_used'], 
                        line['vios_net_rbytes'], line['vios_net_wbytes'], line['vios_net_reads'], line['vios_net_writes'],
                        line['vios_fc_rbytes'], line['vios_fc_wbytes'], line['vios_fc_reads'], line['vios_fc_writes'] ))
                    if lines >3:
                        break
 
        if filename[:16] == "LogicalPartition":
            # print("\n\n----> LPAR level stats .xml (missing the .xml extension) of JSON filenames giving")
            if debug:
                filename2 = filename + ".xml"
                print('\n----> Server=%s Filenames XML File=%d bytes%d name=%s' %(server['name'],num,len(data),filename2))
                hmc.save_to_file(filename2,data)
            else:
                print('\n----> Server=%s Filenames XML File=%d bytes%d' %(server['name'],num,len(data)))

            filename3, url = hmc.get_filename_from_xml(data)
            LPARstats = hmc.get_stats(url, filename3, "LPARstats")

            if debug:
                filename3 = filename3.replace('.json','.JSON')
                print('---> Save readable JSON File=%d bytes=%d name=%s' %(num,len(LPARstats),filename3))
                hmc.save_json_txt_to_file(filename3,LPARstats)

            info = hmc.extract_lpar_info(LPARstats)
            if debug:
                print("----> LPAR")
                print(info)

            header, stats, errors, lines = hmc.extract_lpar_stats(LPARstats)
            if debug:
                print("----> LPAR Records=%d Errors=%d" % (lines,errors))
                print("----> LPAR Header=%s" % (header))
                for lineno,line in enumerate(stats):
                    print("LPAR Line %d" % (lineno))
                    print(line)
                    if lines >3:
                        break

            if output_html:                                              # Create .html file that graphs the stats
                filename = "LPAR-" + info['lparname'] + str(starttime) + ".html"          # Using googlechart
                n = nchart.nchart_open()
                n.nchart_lpar(filename, info, stats)
                print("Created webpage %s" % (filename))

            if output_csv:                                               # Create comma separated vaules file
                filename = "LPAR-" + info['lparname'] + str(starttime) + ".csv"
                f = open(filename,"a")
                f.write("%s\n" %(header))
                for line in stats:
                    f.write("%s, %.2f,%.2f,%.2f, %.1f, %.1f,%.1f,%.1f,%.1f, %.1f,%.1f,%.1f,%.1f\n" % (line['time'], line['cpu_vp'], line['cpu_entitled'], line['cpu_used'], line['mem_conf'], line['net_rbytes'], line['net_wbytes'], line['net_reads'], line['net_writes'], line['disk_rbytes'], line['disk_wbytes'], line['disk_reads'], line['disk_writes'] ))
                f.close()
                print("Saved comma separated values to %s" % (filename))

print("-> tar and cleanup the csv files")
hmc.tar_csv()
print("Logging off the HMC")
hmc.logoff()
