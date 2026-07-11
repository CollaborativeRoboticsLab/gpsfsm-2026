# Academic Project Page Template

## Configuration

### Fork this repo

Click the top fork button to fork the repository.

Select a suitable name for the repository; for example, 'gpsfsm_2026' was used for the paper 'A Generative Partially Specified Finite State Machine Approach to Complex Behaviour Planning' published in 2026. This would appear as [https://collaborativeroboticslab.github.io/gpsfsm-2026/](https://collaborativeroboticslab.github.io/gpsfsm-2026/).

## Publishing the page.

Once the repository has been created, follow the instructions here about [publishing-from-a-branch](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site#publishing-from-a-branch)

- Go to repo's `Settings` -> `Pages` (under `Code and automation` section)
- Under `source` select `deploy from branch`
- Under `branch` select `master` and then `/docs` option and press `save`
- In a few minutes, you will get a new info box with "Your site is now live at..." with the link to the site.

## Customization

The HTML file is at the `/docs/index.html` and has TODO comments showing what to replace:

- Paper title, authors, institution, conference
- Links (arXiv, GitHub, etc.)
- Abstract and descriptions
- Videos, images, and PDFs
- Related works in the dropdown
- Meta tags for SEO and social sharing

### Meta Tags

The template includes meta tags for better search engine visibility and social media sharing. These appear in the `<head>` section and help with:
- Google Scholar indexing
- Social media previews (Twitter, Facebook, LinkedIn)
- Search engine optimization

Create a 1200x630px social preview image at `static/images/social_preview.png`.

## Tips

- Compress images with [TinyPNG](https://tinypng.com)
- Use YouTube for large videos (>10MB)  
- Replace the favicon in `static/images/`
- Works with GitHub Pages

## Acknowledgments
Parts of this project page were adopted from the [Nerfies](https://nerfies.github.io/) page.

## Website License
<a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.
