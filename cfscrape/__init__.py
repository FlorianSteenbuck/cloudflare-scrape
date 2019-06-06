import time
import random
import re
import os
from requests.sessions import Session
import json
try:
    import execjs
    is_execjs_imported = True
except:
    is_execjs_imported = False
    
if not is_execjs_imported:    
    try:
        """
        Name: Js2Py
        Version: 0.37
        Summary: JavaScript to Python Translator & JavaScript interpreter written in 100% pure Python.
        Home-page: https://github.com/PiotrDabkowski/Js2Py
        Author: Piotr Dabkowski
        Author-email: piotr.dabkowski@balliol.ox.ac.uk
        License: MIT
        Description: Translates JavaScript to Python code. Js2Py is able to translate and execute virtually any JavaScript code.
        """
        
        import js2py
    except:
        raise
    
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.84 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:41.0) Gecko/20100101 Firefox/41.0"
]

DEFAULT_USER_AGENT = random.choice(DEFAULT_USER_AGENTS)

def path_to_value(dict_, path, default=None):
    for key in dict_.keys():
        if key != path[0]:
            continue 
        value = dict_[key]
        if type(value) == dict and len(path) != 1:
            return path_to_value(dict_, path[1:])
        elif len(path) == 1:
            return value
    return default
"""
def number_magic(value, index=0):
    number = 0.0
    tail_operator = ""
    working = 
    while index < len(value):
        char = value
        if in ["+","-","*","/","&",">>>","<<",">>","^","&","|"]:
"""

def hira_last_add(ls, appendy):
    append_index = None
    append_list = None

    for x in range(len(ls)):
        if type(ls[x]) == list:
            append_index = x
            append_list = ls[x]

    if type(append_index) == int:
        ls[append_index] = hira_last_add(append_list, appendy)
    else:
        ls.append(appendy)
    return ls

class CloudflareScraper(Session):
    def __init__(self, *args, **kwargs):
        self.js_engine = kwargs.pop("js_engine", None)
        super(CloudflareScraper, self).__init__(*args, **kwargs)

        if "requests" in self.headers["User-Agent"]:
            # Spoof Firefox on Linux if no custom User-Agent has been set
            self.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0"

    def request(self, method, url, *args, **kwargs):
        resp = super(CloudflareScraper, self).request(method, url, *args, **kwargs)
        print(resp.content)
        # Check if Cloudflare anti-bot is on
        if ("URL=/cdn-cgi/" in resp.headers.get("Refresh", "") or
                (resp.status_code == 503 and
                  re.search(r'<form id="challenge-form".+?DDoS protection by CloudFlare', resp.text, re.I | re.DOTALL)
                )
            ): # Sometimes cloud flare sends a 503 status_code with no "Refresh" header for DDos protection.
            return self.solve_cf_challenge(resp, **kwargs)

        # Otherwise, no Cloudflare anti-bot detected
        return resp

    def solve_cf_challenge(self, resp, **kwargs):
        time.sleep(4)  # Cloudflare requires a delay before solving the challenge

        body = resp.text
        parsed_url = urlparse(resp.url)
        path = parsed_url.path
        domain = urlparse(resp.url).netloc
        submit_url = "%s://%s/cdn-cgi/l/chk_jschl" % (parsed_url.scheme, domain)

        params = kwargs.setdefault("params", {})
        headers = kwargs.setdefault("headers", {})
        headers["Referer"] = resp.url

        try:
            params["s"] = re.findall(r'name="s" value="(.+?)"', body)[-1]
            params["jschl_vc"] = re.findall(r'name="jschl_vc" value="(\w+)"', body)[-1]
            params["pass"] = re.findall(r'name="pass" value="(.+?)"', body)[-1]

            # Extract the arithmetic operation
            secret = self.extract_js(body)
            secret += len(domain+path)

            context = js2py.EvalJs({'value': secret})
            context.execute("value = value.toFixed(10);")
            secret = context.value
            print(secret)
            params["jschl_answer"] = secret

        except Exception:
            # Something is wrong with the page.
            # This may indicate Cloudflare has changed their anti-bot
            # technique. If you see this and are running the latest version,
            # please open a GitHub issue so I can update the code accordingly.
            print("[!] Unable to parse Cloudflare anti-bots page. "
                  "Try upgrading cloudflare-scrape, or submit a bug report "
                  "if you are running the latest version. Please read "
                  "https://github.com/Anorov/cloudflare-scrape#updates "
                  "before submitting a bug report.\n")
            raise
        print(kwargs["params"])
        return self.get(submit_url, **kwargs)

    def extract_js(self, body):
        js = re.search(r"setTimeout\(function\(\){\s+(var "
                        "s,t,o,p,b,r,e,a,k,i,n,g,f.+?\r?\n[\s\S]+?a\.value =.+?)\r?\n", body).group(1)
        
        # TODO support add all call method of js_dict
        # TODO regexless
        root_bastard = re.compile('(([ \\t]+|)(;|,|:|=|)([ \t]+|)(var |"|\'|)([ \\t]+|)(?P<key>[A-Za-z.]+)([ \\t]+|)("|\'|)(?P<operator>(:|=|(\\+|\\-|\\*|\\/|\\&|>>>|<<|>>|\\^|\\&|\\|)=))([ \t]+|)((?P<value>[^;]+)(;|,)|))')
        
        statements = []
        for statement in re.finditer(root_bastard, js):
            statements.append(statement.groupdict())

        hidden_value = 0
        find_dotted = "(([A-Za-z0-9]+)((\\.[A-Za-z0-9]+)+))"
        hidden_path = []
        for state in statements:
            if state["key"].strip().endswith(".value"):
                for may_hidden in re.findall(find_dotted, state["value"]):
                    if may_hidden[0].endswith(".length"):
                        continue
                    hidden_path = may_hidden[0].split(".")
                    break

        context = js2py.EvalJs({'value': None})
        calc = None
        hidden_keys = ["[\""+"\"][\"".join(hidden_path)+"\"]", "['"+"']['".join(hidden_path)+"']",".".join(hidden_path)]
        for state in statements:
            is_js_dict = state["value"].strip().startswith("{")
            key = state["key"].strip()
            operator = state["operator"]
            if operator == ":":
                operator = "="
            value = state["value"]
            if (len(hidden_path) > 0 and is_js_dict and key == hidden_path[0]) or (key in hidden_keys):
                if is_js_dict:
                    new_chars = ""
                    last_chars = ""
                    for x in range(len(value)):
                        if last_chars == "\":" or last_chars == "':" or value[x] == ",":
                            new_chars += "\""
                        if len(last_chars) == 2:
                            last_chars = last_chars[1:]
                        last_chars += value[x]
                        new_chars += value[x]
                    if new_chars.endswith("}"):
                        new_chars = new_chars[:len(new_chars)-1]+"\"}"
                    else:
                        new_chars += "\"}"
                    value = path_to_value(json.loads(new_chars), hidden_path[1:])
                if value is None:
                    continue

                print("value"+operator+value)
                context.execute("value"+operator+value)

                """
                region_mess = []
                region_deepness = 0
                last_deepness = -1
                trues = ["!+[]", "!![]"]
                
                collecty = ""
                number = 0
                operator = None
                for char in value:
                    if char == "(":
                        if type(operator) in [str, chr, unicode]:
                            region_mess.append(operator)
                            operator = None
                        region_deepness+=1
                        continue
                    elif char == ")":
                        region_mess.append(number)
                        number = 0
                        collecty = ""
                        operator = ""
                        region_deepness-=1
                        continue

                    if type(operator) == str:
                        operator += char
                    else:
                        collecty += char
                        for true in trues:
                            if collecty.endswith(true):
                                number+=1
                                break
                print(value)
                print(region_mess)
                """
        print(statements)
        print(context.value)
        return context.value

        """
        js = re.sub(r"a\.value = (parseInt\(.+?\)).+", r"\1", js)
        js = re.sub(r"\s{3,}[a-z](?: = |\.).+", "", js)

        # Strip characters that could be used to exit the string context
        # These characters are not currently used in Cloudflare's arithmetic snippet
        js = re.sub(r"[\n\\']", "", js)

        if is_execjs_imported:
            if "Node" in self.js_engine:
                # Use vm.runInNewContext to safely evaluate code
                # The sandboxed code cannot use the Node.js standard library
                return "return require('vm').runInNewContext('%s');" % js
            else:
                return js.replace("parseInt", "return parseInt")
        else:
            return js
        """

    @classmethod
    def create_scraper(cls, sess=None, js_engine=None):
        """
        Convenience function for creating a ready-to-go requests.Session (subclass) object.
        """

        if is_execjs_imported:
            if js_engine:
                os.environ["EXECJS_RUNTIME"] = js_engine

            js_engine = execjs.get().name

            if not ("Node" in js_engine or "V8" in js_engine):
                raise EnvironmentError("Your Javascript runtime '%s' is not supported due to security concerns. "
                                       "Please use Node.js or PyV8. To force a specific engine, "
                                       "such as Node, call create_scraper(js_engine=\"Node\")" % js_engine)

        scraper = cls(js_engine=js_engine)

        if sess:
            attrs = ["auth", "cert", "cookies", "headers", "hooks", "params", "proxies", "data"]
            for attr in attrs:
                val = getattr(sess, attr, None)
                if val:
                    setattr(scraper, attr, val)

        return scraper


    ## Functions for integrating cloudflare-scrape with other applications and scripts

    @classmethod
    def get_tokens(cls, url, user_agent=None, js_engine=None):
        scraper = cls.create_scraper(js_engine=js_engine)
        if user_agent:
            scraper.headers["User-Agent"] = user_agent

        try:
            resp = scraper.get(url)
            resp.raise_for_status()
        except Exception as e:
            print("'%s' returned an error. Could not collect tokens.\n" % url)
            raise

        domain = urlparse(resp.url).netloc
        cookie_domain = None

        for d in scraper.cookies.list_domains():
            if d.startswith(".") and d in ("." + domain):
                cookie_domain = d
                break
        else:
            raise ValueError("Unable to find Cloudflare cookies. Does the site actually have Cloudflare IUAM mode enabled?")

        return ({
                    "__cfduid": scraper.cookies.get("__cfduid", "", domain=cookie_domain),
                    "cf_clearance": scraper.cookies.get("cf_clearance", "", domain=cookie_domain)
                },
                scraper.headers["User-Agent"]
               )

    @classmethod
    def get_cookie_string(cls, url, user_agent=None, js_engine=None):
        """
        Convenience function for building a Cookie HTTP header value.
        """
        tokens, user_agent = cls.get_tokens(url, user_agent=user_agent, js_engine=None)
        return "; ".join("=".join(pair) for pair in tokens.items()), user_agent

create_scraper = CloudflareScraper.create_scraper
get_tokens = CloudflareScraper.get_tokens
get_cookie_string = CloudflareScraper.get_cookie_string
