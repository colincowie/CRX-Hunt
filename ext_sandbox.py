# @th3_protoCOL
import os, time, asyncio, threading, requests, zipfile
from selenium import webdriver
from multiprocessing import Process
from mitmproxy.options import Options
from mitmproxy.proxy.config import ProxyConfig
from mitmproxy.proxy.server import ProxyServer
from mitmproxy.tools.dump import DumpMaster

class EXT_Sandbox():
    def __init__(self,ext_id,time):
        self.ext_id = ext_id
        self.time = time
        if not os.path.exists('output'):
            os.makedirs('output')
        if not os.path.exists("reports"):
            os.makedirs("reports")
        if not os.path.exists("reports/"+self.ext_id+"/"):
            os.makedirs("reports/"+self.ext_id+"/")


        pass

    def download_ext(self, id):
        # Download extension webstore url
        download_url = "https://clients2.google.com/service/update2/crx?response=redirect&os=win&arch=x86-64&os_arch=x86-64&nacl_arch=x86-64&prod=chromecrx&prodchannel=unknown&prodversion=81.0.4044.138&acceptformat=crx2,crx3&x=id%3D" + id + "%26uc"
        print("[*] Downloading extension with id: "+id)
        r = requests.get(download_url, allow_redirects=True)

        # Save output of download
        if r.status_code == 200 :
            # Save ext to .crx file
            crx = os.path.join('output', id)+'.crx'
            open(crx, 'wb').write(r.content)
            print("[*] Unzipping Extension")
            try:
                with zipfile.ZipFile(crx, 'r') as zip_ref:
                    zip_ref.extractall(crx[:-4])
                os.remove(crx)
            except Exception as e:
                print("[-] Unzip Error")
                print(e)
                print(download_url)
                pass
            return True
        elif r.status_code == 204:
            print("[-] HTTP 204: No Content.")
            return False
        else:
            print("[-] Error! Status Code: "+str(r.status_code))
            return False

    def run(self):
        id = self.ext_id
        requests.put('http://localhost:9200/mitm')
        mitm = self.start_mitm()
        ext_download = self.download_ext(id)
        if ext_download:
            print("[*] Creating chrome webdriver")
            # Create the webdriver with proxy and extension
            options = webdriver.ChromeOptions()
            # Load chrome extension
            options.add_argument('load-extension='+os.path.abspath("output")+'/'+str(id));
            options.add_argument('--proxy-server=127.0.0.1:8080')
            options.add_argument('--allow-running-insecure-content')
            options.add_argument('--ignore-certificate-errors')
            #options.add_experimental_option("detach", True)
            driver = webdriver.Chrome(options=options)
            print("\u001b[40m\u001b[32m[↓]\u001b[0m\u001b[40m Sandbox Network Request \u001b[32m[↓]\u001b[0m\u001b[0m")

            driver.get("chrome://extensions/?id="+id)
            print("[*] Sleeping while extension is running")
            time.sleep(self.time)
            print('[*] Shutting down mitmproxy...')
            mitm.shutdown()
            return True

    def start_mitm(self):
            asyncio.set_event_loop(asyncio.new_event_loop())
            print('[*] Starting mitmproxy on 127.0.0.1:8080')
            options = Options(listen_host='127.0.0.1', listen_port=8080, http2=True)
            m = DumpMaster(options, with_termlog=False, with_dumper=False)
            config = ProxyConfig(options)
            m.server = ProxyServer(config)
            addon = MitmAddon(self.ext_id)
            m.addons.add(addon)
            # run mitmproxy in backgroud
            loop = asyncio.new_event_loop()
            t = threading.Thread( target=loop_in_thread, args=(loop,m) )
            t.start()
            return m

# Addon class for Mitmproxy recording
class MitmAddon(object):
    def __init__(self,ext_id):
        self.ext_id = ext_id
        self.num = 1

    def request(self, flow):
        output = "reports/"+self.ext_id+"/mitm_urls.txt"
        flow.request.headers["count"] = str(self.num)
        print("\033[0;35m[request] \033[0m"+flow.request.url)
        # Save reques to data (format [VERB, url])

        with open(output, 'a') as f:
            f.write(str(flow.request.method) + ' ' + str(flow.request.url) + ' ' + '\n')

    def response(self, flow):
        self.num = self.num + 1
        flow.response.headers["count"] = str(self.num)

        url = flow.request.url

        output = "reports/"+self.ext_id+"/mitm_content.txt"
        with open(output, 'a') as f:
            f.write(str(flow.request.method) + ' ' + str(flow.request.url) +  '\n')
            f.write("--------")
            for k, v in flow.request.headers.items():
                f.write('\n' + str(flow.request.content.decode('utf-8')) + '\n')
                for k, v in flow.response.headers.items():
                    f.write('\n' + str(flow.response.content.decode('utf-8')) + '\n')


# function used for proxy async - source: https://gist.github.com/BigSully/3da478792ee331cb2e5ece748393f8c4
def loop_in_thread(loop, m):
    asyncio.set_event_loop(loop)
    m.run_loop(loop.run_forever)

if __name__ == "__main__":
    ext = input("[!] Please provide a chrome extension id: ")
    # Create instance of the sandbox class and run with an extension id
    box = EXT_Sandbox(ext, 60)
    box.run()
