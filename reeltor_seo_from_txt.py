import scrapy
import json
from scrapy.http import Request
from urllib.parse import urlparse


class ReeltorSeoItem(scrapy.Item):
    url = scrapy.Field()
    status_code = scrapy.Field()
    final_url = scrapy.Field()
    redirect_chain = scrapy.Field()
    response_time_ms = scrapy.Field()
    page_size_kb = scrapy.Field()

    title = scrapy.Field()
    title_length = scrapy.Field()
    meta_description = scrapy.Field()
    meta_description_length = scrapy.Field()
    meta_keywords = scrapy.Field()
    meta_robots = scrapy.Field()
    canonical_url = scrapy.Field()
    viewport = scrapy.Field()
    hreflang = scrapy.Field()
    html_lang = scrapy.Field()

    h1 = scrapy.Field()
    h1_count = scrapy.Field()
    h2_count = scrapy.Field()
    has_h1 = scrapy.Field()
    number_of_paragraphs = scrapy.Field()
    word_count = scrapy.Field()

    total_images = scrapy.Field()
    images_without_alt = scrapy.Field()
    image_urls = scrapy.Field()
    lazy_image_urls = scrapy.Field()
    webp_image_urls = scrapy.Field()
    wh_image_urls = scrapy.Field()

    total_links = scrapy.Field()
    internal_links = scrapy.Field()
    external_links = scrapy.Field()
    nofollow_links = scrapy.Field()
    internal_links_list = scrapy.Field()
    external_links_list = scrapy.Field()
    other_links_list = scrapy.Field()

    og_title = scrapy.Field()
    og_description = scrapy.Field()
    og_image = scrapy.Field()
    og_url = scrapy.Field()
    twitter_card = scrapy.Field()
    og_present = scrapy.Field()

    schema_json_ld = scrapy.Field()
    schema_count = scrapy.Field()
    schema_types = scrapy.Field()

    is_indexable = scrapy.Field()
    has_self_canonical = scrapy.Field()
    last_modified = scrapy.Field()
    content_type = scrapy.Field()
    has_video = scrapy.Field()

    h3_count = scrapy.Field()
    h4_count = scrapy.Field()
    h5_count = scrapy.Field()
    h6_count = scrapy.Field()
    h2_texts = scrapy.Field()

    url_length = scrapy.Field()
    url_depth = scrapy.Field()
    url_has_https = scrapy.Field()

    twitter_title = scrapy.Field()
    twitter_description = scrapy.Field()
    twitter_image = scrapy.Field()

    og_type = scrapy.Field()
    og_site_name = scrapy.Field()

    x_robots_tag = scrapy.Field()
    cache_control = scrapy.Field()
    server = scrapy.Field()
    x_vercel_cache = scrapy.Field()
    cdn_cache_control = scrapy.Field()
    surrogate_key = scrapy.Field()
    age_seconds = scrapy.Field()
    cf_cache_status = scrapy.Field()
    pragma = scrapy.Field()

    rel_next = scrapy.Field()
    rel_prev = scrapy.Field()

    amp_url = scrapy.Field()
    has_amp = scrapy.Field()

    has_favicon = scrapy.Field()

    ul_count = scrapy.Field()
    ol_count = scrapy.Field()
    table_count = scrapy.Field()
    has_faq_section = scrapy.Field()

    images_with_lazy_load = scrapy.Field()
    images_with_width_height = scrapy.Field()
    webp_images = scrapy.Field()

    has_nosnippet = scrapy.Field()
    has_noarchive = scrapy.Field()

    has_faq_schema = scrapy.Field()
    has_breadcrumb_schema = scrapy.Field()
    has_real_estate_schema = scrapy.Field()

    has_price = scrapy.Field()
    has_map = scrapy.Field()
    listing_count = scrapy.Field()


class ReeltorSeoSpider(scrapy.Spider):
    name = 'reeltor_seo_from_txt'
    # No allowed_domains — we analyse any URLs provided in the input file

    custom_settings = {
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 0.1,
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/133.0.0.0 Safari/537.36'
        ),

        'TWISTED_REACTOR': 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',

        'DOWNLOADER_HANDLERS': {
            'http':  'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
            'https': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
        },

        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 60000,
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'PLAYWRIGHT_HEADLESS': True,

        'LOG_LEVEL': 'INFO',

        # Let 4xx / 5xx responses reach parse_item instead of being dropped,
        # so the real status code (and the error page's HTML) is recorded.
        'HTTPERROR_ALLOW_ALL': True,
    }

    def __init__(self, urls_file='urls.txt', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.urls_file = urls_file
        self.start_urls = []
        try:
            with open(self.urls_file, 'r', encoding='utf-8') as f:
                self.start_urls = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith('#')
                ]
            self.logger.info(f"{len(self.start_urls)} URLs loaded from {self.urls_file}")
        except FileNotFoundError:
            self.logger.error(f"URL file not found: {self.urls_file}")

    def start_requests(self):
        for url in self.start_urls:
            if url:
                yield Request(
                    url=url,
                    callback=self.parse_item,
                    errback=self.handle_error,
                    dont_filter=True,
                    meta={
                        "playwright": True,
                        "playwright_page_methods": [
                            ("wait_for_load_state", "networkidle"),
                        ],
                    }
                )

    def handle_error(self, failure):
        url = failure.request.url
        self.logger.error(f"Error on {url}: {failure.value}")
        item = ReeltorSeoItem()
        item['url'] = url
        # Keep the real HTTP status when there is a response (e.g. HttpError);
        # only genuine network failures (DNS, timeout, connection reset) stay 'ERROR'.
        response = getattr(failure.value, 'response', None)
        item['status_code'] = response.status if response is not None else 'ERROR'
        item['final_url'] = response.url if response is not None else url
        yield item

    def parse_item(self, response):
        item = ReeltorSeoItem()

        item['url'] = response.request.url
        item['status_code'] = response.status
        item['final_url'] = response.url
        item['redirect_chain'] = response.request.meta.get('redirect_urls', [])
        item['response_time_ms'] = round(response.meta.get('download_latency', 0) * 1000, 2)
        item['page_size_kb'] = round(len(response.body) / 1024, 2)

        item['title'] = response.css('title::text').get(default='').strip()
        item['title_length'] = len(item['title'])
        item['meta_description'] = response.css('meta[name="description"]::attr(content)').get(default='')
        item['meta_description_length'] = len(item['meta_description'])
        item['meta_keywords'] = response.css('meta[name="keywords"]::attr(content)').get(default='')
        item['meta_robots'] = response.css('meta[name="robots"]::attr(content)').get(default='')
        item['canonical_url'] = response.css('link[rel="canonical"]::attr(href)').get(default='')
        item['viewport'] = response.css('meta[name="viewport"]::attr(content)').get(default='')
        item['hreflang'] = response.css('link[rel="alternate"][hreflang]::attr(hreflang)').getall()
        item['html_lang'] = response.css('html::attr(lang)').get(default='')

        item['h1'] = response.css('h1::text').get(default='').strip()
        item['h1_count'] = len(response.css('h1'))
        item['h2_count'] = len(response.css('h2'))
        item['has_h1'] = item['h1_count'] > 0
        item['number_of_paragraphs'] = len(response.css('p'))

        item['h3_count'] = len(response.css('h3'))
        item['h4_count'] = len(response.css('h4'))
        item['h5_count'] = len(response.css('h5'))
        item['h6_count'] = len(response.css('h6'))
        item['h2_texts'] = [t.strip() for t in response.css('h2::text').getall() if t.strip()]

        body_text = ' '.join(response.xpath('//body//text()').getall())
        body_text = ' '.join(body_text.split())
        item['word_count'] = len(body_text.split())

        images = response.css('img')
        item['total_images'] = len(images)
        item['images_without_alt'] = len([img for img in images if not img.attrib.get('alt', '').strip()])
        item['images_with_lazy_load'] = len(response.css('img[loading="lazy"]'))
        item['images_with_width_height'] = len([
            img for img in images
            if img.attrib.get('width') and img.attrib.get('height')
        ])
        item['webp_images'] = len(response.css('img[src*=".webp"], source[type="image/webp"]'))
        from urllib.parse import urljoin
        item['image_urls'] = list(dict.fromkeys(
            urljoin(response.url, src)
            for img in images
            for src in [img.attrib.get('src', '').strip()]
            if src
        ))
        item['lazy_image_urls'] = list(dict.fromkeys(
            urljoin(response.url, img.attrib.get('src', '').strip())
            for img in images
            if img.attrib.get('loading', '').lower() == 'lazy' and img.attrib.get('src', '').strip()
        ))
        item['webp_image_urls'] = list(dict.fromkeys(
            urljoin(response.url, src)
            for img in response.css('img[src*=".webp"], source[type="image/webp"]')
            for src in [img.attrib.get('src', img.attrib.get('srcset', '')).strip()]
            if src
        ))
        item['wh_image_urls'] = list(dict.fromkeys(
            urljoin(response.url, img.attrib.get('src', '').strip())
            for img in images
            if img.attrib.get('width') and img.attrib.get('height') and img.attrib.get('src', '').strip()
        ))

        all_links = response.css('a::attr(href)').getall()
        parsed = urlparse(response.url)
        base_domain = parsed.netloc
        internal = [l for l in all_links if base_domain in l or l.startswith('/')]
        external = [l for l in all_links if l.startswith(('http', '//')) and base_domain not in l]
        other = [l for l in all_links if l not in internal and l not in external]
        # deduplicate lists — counts are derived from these so they always match the tabs
        internal_list = list(dict.fromkeys(internal))
        external_list = list(dict.fromkeys(external))
        other_list    = list(dict.fromkeys(other))
        item['internal_links_list'] = internal_list
        item['external_links_list'] = external_list
        item['other_links_list']    = other_list
        item['internal_links'] = len(internal_list)
        item['external_links'] = len(external_list)
        item['total_links']    = len(internal_list) + len(external_list) + len(other_list)
        item['nofollow_links'] = len(response.css('a[rel*="nofollow"]'))

        item['og_title'] = response.css('meta[property="og:title"]::attr(content)').get(default='')
        item['og_description'] = response.css('meta[property="og:description"]::attr(content)').get(default='')
        item['og_image'] = response.css('meta[property="og:image"]::attr(content)').get(default='')
        item['og_url'] = response.css('meta[property="og:url"]::attr(content)').get(default='')
        item['og_type'] = response.css('meta[property="og:type"]::attr(content)').get(default='')
        item['og_site_name'] = response.css('meta[property="og:site_name"]::attr(content)').get(default='')
        item['twitter_card'] = response.css('meta[name="twitter:card"]::attr(content)').get(default='')
        item['twitter_title'] = response.css('meta[name="twitter:title"]::attr(content)').get(default='')
        item['twitter_description'] = response.css('meta[name="twitter:description"]::attr(content)').get(default='')
        item['twitter_image'] = response.css('meta[name="twitter:image"]::attr(content)').get(default='')
        item['og_present'] = bool(item['og_title'] or item['og_description'])

        schemas = response.css('script[type="application/ld+json"]::text').getall()
        item['schema_count'] = len(schemas)
        item['schema_json_ld'] = 'YES' if schemas else 'NO'
        schema_types = []
        for s in schemas:
            try:
                d = json.loads(s)
                if isinstance(d, dict):
                    schema_types.append(d.get('@type'))
                elif isinstance(d, list):
                    for entry in d:
                        if isinstance(entry, dict):
                            schema_types.append(entry.get('@type'))
            except Exception:
                pass
        item['schema_types'] = list(set(filter(None, schema_types)))
        item['has_faq_schema'] = 'FAQPage' in item['schema_types']
        item['has_breadcrumb_schema'] = 'BreadcrumbList' in item['schema_types']
        item['has_real_estate_schema'] = any('RealEstate' in str(t) for t in item['schema_types'])

        robots_lower = item['meta_robots'].lower()
        item['is_indexable'] = 'noindex' not in robots_lower
        item['has_self_canonical'] = (item['canonical_url'] == response.url) or (not item['canonical_url'])
        item['has_nosnippet'] = 'nosnippet' in robots_lower
        item['has_noarchive'] = 'noarchive' in robots_lower

        item['last_modified'] = response.headers.get('Last-Modified', b'').decode('utf-8', errors='ignore')
        item['content_type'] = response.headers.get('Content-Type', b'').decode('utf-8', errors='ignore')
        item['x_robots_tag'] = response.headers.get('X-Robots-Tag', b'').decode('utf-8', errors='ignore')
        item['cache_control'] = response.headers.get('Cache-Control', b'').decode('utf-8', errors='ignore')
        item['server'] = response.headers.get('Server', b'').decode('utf-8', errors='ignore')
        item['x_vercel_cache'] = response.headers.get('X-Vercel-Cache', b'').decode('utf-8', errors='ignore')
        item['cdn_cache_control'] = response.headers.get('CDN-Cache-Control', b'').decode('utf-8', errors='ignore')
        item['surrogate_key'] = response.headers.get('Surrogate-Key', response.headers.get('Cache-Tag', b'')).decode('utf-8', errors='ignore')
        item['age_seconds'] = response.headers.get('Age', b'').decode('utf-8', errors='ignore')
        item['cf_cache_status'] = response.headers.get('CF-Cache-Status', b'').decode('utf-8', errors='ignore')
        item['pragma'] = response.headers.get('Pragma', b'').decode('utf-8', errors='ignore')

        item['has_video'] = len(response.css('video, iframe[src*="youtube"], iframe[src*="reel"]')) > 0

        item['url_length'] = len(response.url)
        item['url_depth'] = parsed.path.rstrip('/').count('/')
        item['url_has_https'] = response.url.startswith('https')

        item['rel_next'] = response.css('link[rel="next"]::attr(href)').get(default='')
        item['rel_prev'] = response.css('link[rel="prev"]::attr(href)').get(default='')

        item['amp_url'] = response.css('link[rel="amphtml"]::attr(href)').get(default='')
        item['has_amp'] = bool(item['amp_url'])

        item['has_favicon'] = bool(response.css('link[rel*="icon"]').get())

        item['ul_count'] = len(response.css('ul'))
        item['ol_count'] = len(response.css('ol'))
        item['table_count'] = len(response.css('table'))
        item['has_faq_section'] = bool(response.css('[class*="faq"], [id*="faq"]').get())

        item['has_price'] = bool(response.css('[class*="price"], [itemprop="price"]').get())
        item['has_map'] = bool(response.css('iframe[src*="maps.google"], iframe[src*="maps"]').get())
        item['listing_count'] = len(response.css('[class*="listing-card"], [class*="property-card"]'))

        yield item
