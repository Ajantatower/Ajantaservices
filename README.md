# Ajanta Tower — open accounts

The public accounts page for Ajanta Services Association. Every rupee collected
and every rupee spent, with a name and a date on it.

## How this repository works

You edit **one file**. Everything else is built for you.

    data/slim.json     <- the whole register: owners, payments, expenses
    src/template.html  <- the site itself (only changes when the design changes)
    build.py           <- turns the two above into the finished site
    _site/             <- the built site (never edited by hand, never committed)

When anything is pushed, GitHub runs `build.py` and publishes the result. That
build produces:

* `index.html` — the accounts page
* `o/<key>.html` and `o/<key>.png` — a page and a preview card for each of the
  54 owners, so a WhatsApp message shows their own name and their own balance
* `preview.png` — the card for the site's own link
* `whatsapp-messages.txt` — a ready message per owner

## Updating the figures

1. Open `data/slim.json` here on GitHub and press the pencil to edit it.
2. Change the numbers.
3. Press **Commit changes**.

The site rebuilds itself within a couple of minutes. Nothing else to do — the
owner pages and their preview cards are regenerated with the new amounts.

## Why the site address is not written anywhere

Preview cards have to carry an absolute address, because the crawler that reads
them cannot run JavaScript. Rather than writing that address into 54 files by
hand, the workflow asks GitHub for this site's own address and passes it to the
build. Move the repository or rename it and everything still points to the right
place.

## Running the build locally

    pip install pillow
    python3 build.py https://your-site-address

The finished site appears in `_site/`.
