# papercut_alerts
prototype alerts for papercut, utilising it's server api.

***NOTE:*** This script is being used as part of a learning process, so it's likely not using the design pattern intented from papercut. If you're looking for python examples, please read the papercut doco on their website.

## Dev Mode

If you don't have access to the papercut api, set the `devMode = True` in the script.

Then in a new console, navigate to the location of your script and run:
	cd ./data && python3 -m SimpleHTTPServer

This runs python's SimpleHTTPServer on localhost:8000, using the ./data directory as it's DocumentRoot.

Don't forget to set it back to False once you've finished testing.
