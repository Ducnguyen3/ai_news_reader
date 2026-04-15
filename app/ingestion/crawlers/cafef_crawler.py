from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.ingestion.crawlers.base_crawler import BaseCrawler, FetchResult
from app.ingestion.parsers.common import (
    ParsedArticle,
    clean_text,
    clean_text_list,
    extract_breadcrumb_names,
    find_news_article_json_ld,
    get_meta_content,
    join_url,
    parse_datetime,
)


class CafeFCrawler(BaseCrawler):
    source_name = "cafef"
    domain = "cafef.vn"
    homepage_url = "https://cafef.vn"
    category_paths = [
        "doanh-nghiep.chn",
        "vi-mo-dau-tu.chn",
        "thi-truong-chung-khoan.chn",
        "tai-chinh-ngan-hang.chn",
        "tai-chinh-quoc-te.chn",
        "kinh-te-so.chn",
        "thi-truong.chn",
        "bat-dong-san.chn",
    ]
    article_url_pattern = re.compile(r"^https://cafef\.vn/.+?-\d+\.chn$")

    def fetch_homepage(self) -> FetchResult:
        return self._request(self.homepage_url)

    def build_category_page_urls(self, category_path: str, page_number: int) -> list[str]:
        base_url = f"{self.homepage_url}/{category_path}"
        category_slug = category_path.removesuffix(".chn")
        if page_number == 1:
            return [base_url]
        return [
            f"{self.homepage_url}/{category_slug}/trang-{page_number}.chn",
            f"{self.homepage_url}/{category_slug}/trang-{page_number}.html",
            f"{base_url}?page={page_number}",
            f"{base_url}?trang={page_number}",
            f"{base_url}?p={page_number}",
        ]

    def extract_article_links(self, homepage_html: str) -> list[str]:
        soup = BeautifulSoup(homepage_html, "lxml")
        links = [join_url(self.homepage_url, tag.get("href")) for tag in soup.select("a[href]")]
        return self.normalize_links(
            link
            for link in links
            if link
            and self.article_url_pattern.search(link)
            and "/du-lieu/" not in link
            and "/timeline/" not in link
            and "/photo-story/" not in link
        )

    def parse_article(self, html: str, url: str) -> ParsedArticle:
        soup = BeautifulSoup(html, "lxml")
        json_ld = find_news_article_json_ld(soup) or {}
        title_node = soup.select_one("h1.title") or soup.select_one("h1")
        summary_node = soup.select_one(".sapo") or soup.select_one(".detail-sapo")
        content_nodes = soup.select(".detail-content p, .contentdetail p")
        author_nodes = soup.select(".author, .author-info, .name")
        category_nodes = soup.select(".bread-crumb li a, .breadcrumb li a, .zone-title a, .category-page__name, .sub_cate a")
        tag_nodes = soup.select(".tag a, .tags a")
        category_names = clean_text_list(node.get_text(" ", strip=True) for node in category_nodes)
        if not category_names:
            category_names = extract_breadcrumb_names(soup)

        return ParsedArticle(
            source_name=self.source_name,
            article_url=url,
            canonical_url=(
                get_meta_content(soup, "property", "og:url")
                or (soup.find("link", rel="canonical") or {}).get("href")
                or url
            ),
            title=clean_text(
                get_meta_content(soup, "property", "og:title")
                or json_ld.get("headline")
                or (title_node.get_text(" ", strip=True) if title_node else "")
            ),
            summary=clean_text(
                get_meta_content(soup, "property", "og:description")
                or (summary_node.get_text(" ", strip=True) if summary_node else "")
            )
            or None,
            content_text=clean_text(" ".join(node.get_text(" ", strip=True) for node in content_nodes)),
            publish_time=parse_datetime(
                get_meta_content(soup, "property", "article:published_time")
                or json_ld.get("datePublished")
                or (soup.select_one(".pdate") and soup.select_one(".pdate").get_text(" ", strip=True))
            ),
            author_names=clean_text_list(node.get_text(" ", strip=True) for node in author_nodes),
            category_names=category_names,
            main_image_url=get_meta_content(soup, "property", "og:image"),
            tags=clean_text_list(node.get_text(" ", strip=True) for node in tag_nodes),
            updated_time=parse_datetime(
                get_meta_content(soup, "property", "article:modified_time")
                or json_ld.get("dateModified")
            ),
        )


__all__ = ["CafeFCrawler"]
