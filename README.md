# rss-forward

Application provides RSS channel for content scraped from web pages.
Web pages could require authentication and that do not discourage us from receiving desired information.
Moreover, by using supported KeePassXC it is simple to mimic *Single Sign-On* authentication to many servces.

RSS provided by the application can be used for example in *Thunderbird* or other feed reader.

Main motivation to create this project was discouragement towards web services that do not provide any kinds of
notifications forcing users to constant login and check for new information.


## Running

To run application simply execute `rssforward.py` script with config file as follows:
```
rssforward.py -c <apth_to_config.toml>
```


## Config file

There is [example configuration file](examples/config_example.toml) in examples. It has following content:
```
#
# example of configuration file
#

[general]
port = 8080             # RSS feed port
refreshtime = 3600      # time in seconds
dataroot = "data"       # relative path to current working directory (absolute path possible)
                        # default value is app dir inside user home directory

[site.librus]
enabled = true                      # enable or disable scraper
auth.type = "RAW"                   # authenticate by providing unencrypted user and password
auth.user = "user123@librus.com"    # login example
auth.pass = "user_secret"           # password example

[site.earlystage]
enabled = true                                              # enable or disable scraper
auth.type = "KEEPASSXC"                                     # authenticate by accessing keepassxc deamon
auth.itemurl = "https://online.earlystage.pl/logowanie/"    # URL of keepassxc item (proper user/pass is identified by the URL)
``` 
Fields are quite self-descriptive. There are two possible methods of authentication:
- raw data stored inside the file
- KeePassXC deamon.

For KeePassXC there is `itemurl` field identifying item in the database.


## How can I prepare new scraper?

Every webpage is different and uses different authentication protocol. Simple way is to use *Web Developer Tools*
(*Network Monitor*) with *Firefox* or *Chrome* and look for endpoints and authentication steps. Moreover every 
request can be exported as *cURL* request.
There can be problem if website requires *JavaScript* to operate. To determine is *JS* is required to authenticate or
scrap data execute earlier mentioned *cURL* requests (in command line). If they succees then it means that JS is not
required and just `requests` library can be used.


## How to add new generator/scraper?

It's quite easy. Just put scraper module inside `rssforward.site` package. The module have to contain free function
`get_generator()` returning instance/object of the scraper. Moreover scraper class have to inherit from `RSSGenerator`
class. Then comes difficult part: implementation of the scraper.

There is `earlystageapi.py` demostrating how to access restricted data using `requests`.


## Similar projects

- [web_scraping_example](https://github.com/mattdood/web_scraping_example)
- [rss-proxy](https://github.com/damoeb/rss-proxy)
- [rss-bridge](https://github.com/RSS-Bridge/rss-bridge)
- [feedbridge](https://github.com/dewey/feedbridge)


## References

- [Building an RSS feed scraper with Python](https://codeburst.io/building-an-rss-feed-scraper-with-python-73715ca06e1f)
- [How to build a RSS from scraping using Python](https://medium.com/@pescadordigital/how-to-build-a-rss-from-scraping-using-python-a8ba798aac84)
- [keepassxc-browser](https://github.com/hrehfeld/python-keepassxc-browser)
- [librus-apix](https://github.com/RustySnek/librus-apix)


## License

BSD 3-Clause License

Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
