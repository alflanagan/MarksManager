# Marks Manager -- Streamline Your Firefox Bookmarks

Both Firefox and Chrome now have options to synchronize your bookmarks across multiple devices. Before that, I was using a third-party service to do the same thing. It's very helpful when you have hundreds of bookmarks (yeah, I know).

What do all these solutions have in common? Synchronization glitches. I ended up with duplicate bookmarks and even duplicated subtrees. And every so often a link dies, but the bookmark remains, pointing to nothing useful.

Marks Manager is an attempt at a solution. Previously, Firefox would export your bookmarks to a pseudo-HTML document, and it presented a bit of a parsing challenge.

## Firefox Gets Smart

Now, Firefox will back up your bookmarks to a beautifly simple JSON format, and restore from the same. So i put some Python scripts together.

## What Can This Do?

Current features include:

1. Import a Firefox backup file.

2. Report duplicate bookmarks (i.e. bookmarks with the same URL) and even detect duplicate folders (where the contained bookmarks ahave matching URLs).

3. Attempt to retrieve the URL for each bookmark, and report any problems encountered.

## Roadmap

Things to add:

1. Automatically remove failing bookmarks, write to new file. (Need to be cautious with this, could remove sites that are only down temporarily).

2. For duplicate folders or bookmarks, prompt the user to pick one to keep and delete others. Write to new file.


4. Intelligent merge of 2 or more backup files.

## Alpha!

This is alpha software, if I'm being generous. "It worked for me"
