# The Afterparty Connector

The Afterparty Connector is a small Chrome extension.
It gives your Partiful sign-in to Afterparty one time, when you select **Connect Partiful**.
After that, the Afterparty server reads your events without the connector.

## What the connector does

1. An Afterparty page sends the message `getPartifulSession` to the connector.
2. The connector makes sure that the page comes from an allowed address.
3. The connector opens partiful.com in a background tab, if no Partiful tab is open.
4. The connector reads the Firebase sign-in record that the Partiful web app keeps in the browser.
5. The connector sends the Partiful user ID, the sign-in token and the display name to the page.
6. The page sends the data to the Afterparty server. The server encrypts the token before it keeps it.

The connector does not keep data. It does not read data from other websites.
It has two permissions: `scripting`, and host access to `https://partiful.com/*`.

## Allowed addresses

Chrome lets a web page send messages to an extension only if the manifest lists the address of the page.
The list is in `externally_connectable.matches` in `manifest.json`.

| Build | Allowed addresses |
|-------|-------------------|
| The folder `extension/` | `http://localhost` and `http://127.0.0.1`, all ports |
| `/afterparty-extension.zip` from an instance | The `PUBLIC_URL` of that instance only |

An instance makes its zip file when a user downloads it. Thus each instance gives out a connector for its own address.

## Load the connector from an instance

1. In Afterparty, open the setup page. Select **Download the connector**.
2. Unzip the file. You get the folder `afterparty-extension`.
3. In Chrome, open `chrome://extensions`.
4. Set **Developer mode** to on.
5. Select **Load unpacked** and select the folder `afterparty-extension`.
6. Go back to Afterparty. The setup page finds the connector.

Use the same steps in other Chromium browsers, for example Arc, Brave and Edge.

## Load the connector for local work

1. Open `chrome://extensions` and set **Developer mode** to on.
2. Select **Load unpacked** and select the folder `extension/` of this repository.

After you change a file in `extension/`, select the reload button of the connector on `chrome://extensions`.

## Extension ID

The manifest has a `key`. The key gives the connector the same ID on each computer: `cihpibcfmplfjcoehgnldjlphjmkajdn`.
The server finds this ID in `extension/manifest.json`. You do not have to set `EXTENSION_ID` for it.

## Publish your connector in the Chrome Web Store

Users of a published connector do not use Developer mode.

1. Make the store package:

   ```bash
   uv run python scripts/package_extension.py dist/connector-store.zip --url https://afterparty.example.com --store
   ```

2. Upload the zip file in the [Chrome Web Store developer dashboard](https://chrome.google.com/webstore/devconsole).
3. Write the privacy answers. The connector reads a sign-in token, so the review looks at it carefully.
4. After the store accepts the item, add its item ID to `EXTENSION_ID`. Keep the unpacked ID first:

   ```bash
   EXTENSION_ID=cihpibcfmplfjcoehgnldjlphjmkajdn,YOUR_STORE_ITEM_ID
   CONNECTOR_STORE_URL=https://chromewebstore.google.com/detail/YOUR_STORE_ITEM_ID
   ```

The `--store` option removes the `key` from the manifest, because the store does not accept it. The store gives the item a new ID.

## Change the permissions

If you change `externally_connectable` or the permissions, increase `version` in `extension/manifest.json`.
Users must then load the new connector.
