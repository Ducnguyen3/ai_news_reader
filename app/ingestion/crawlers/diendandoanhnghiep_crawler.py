from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.ingestion.crawlers.base_crawler import BaseCrawler, FetchResult
from app.ingestion.parsers.common import (
    ParsedArticle,
    clean_text,
    clean_text_list,
    find_news_article_json_ld,
    get_meta_content,
    join_url,
    parse_datetime,
)


class DienDanDoanhNghiepCrawler(BaseCrawler):
    source_name = "diendandoanhnghiep"
    domain = "diendandoanhnghiep.vn"
    homepage_url = "https://diendandoanhnghiep.vn"
    category_paths = [
        "chinh-tri-xa-hoi/kinh-te",
        "doanh-nghiep",
        "bat-dong-san",
        "ngan-hang-chung-khoan/tai-chinh-doanh-nghiep",
        "kinh-doanh-quoc-te/kinh-te-the-gioi",
        "chinh-tri-xa-hoi/nghien-cuu-trao-doi",
    ]
    article_url_pattern = re.compile(r"^https://diendandoanhnghiep\.vn/.+?-\d+\.html$")

    def fetch_homepage(self) -> FetchResult:
        return self._request(self.homepage_url)

    def build_category_page_urls(self, category_path: str, page_number: int) -> list[str]:
        base_url = f"{self.homepage_url}/{category_path}"
        if page_number == 1:
            return [base_url]
        return [
            f"{base_url}?page={page_number}",
            f"{base_url}?p={page_number}",
            f"{base_url}/trang-{page_number}",
            f"{base_url}/trang-{page_number}.html",
            f"{base_url}/page/{page_number}",
        ]

    def extract_article_links(self, homepage_html: str) -> list[str]:
        soup = BeautifulSoup(homepage_html, "lxml")
        links = [join_url(self.homepage_url, tag.get("href")) for tag in soup.select("a[href]")]
        return self.normalize_links(
            link
            for link in links
            if link
            and self.article_url_pattern.search(link)
            and "/tag/" not in link
            and "/video/" not in link
        )

    def parse_article(self, html: str, url: str) -> ParsedArticle:
        soup = BeautifulSoup(html, "lxml")
        json_ld = find_news_article_json_ld(soup) or {}
        title_node = soup.select_one("h1.detail-title") or soup.select_one("h1")
        summary_node = soup.select_one(".detail-sapo") or soup.select_one(".sapo")
        content_nodes = soup.select(".detail-content p, .news-content p, article p")
        author_nodes = soup.select(".detail-author, .author, .name")
        category_nodes = soup.select(".breadcrumb a, .detail-cate a")
        tag_nodes = soup.select(".detail-tag a, .tags a")

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
                or (soup.select_one("time") and soup.select_one("time").get("datetime"))
            ),
            author_names=clean_text_list(node.get_text(" ", strip=True) for node in author_nodes),
            category_names=clean_text_list(node.get_text(" ", strip=True) for node in category_nodes),
            main_image_url=get_meta_content(soup, "property", "og:image"),
            tags=clean_text_list(node.get_text(" ", strip=True) for node in tag_nodes),
            updated_time=parse_datetime(
                get_meta_content(soup, "property", "article:modified_time")
                or json_ld.get("dateModified")
            ),
        )


__all__ = ["DienDanDoanhNghiepCrawler"]
