import streamlit as st
from data_sources.trends import fetch_trends_data
from data_sources.serper import fetch_serper_data
from data_sources.reddit import fetch_reddit_complaints
from cache.disk_cache import get_cached, set_cached, clear_all


def cached_trends(keyword: str, timeframe: str = "today 3-m", geo: str = ""):
    key = f"trends::{keyword}::{timeframe}::{geo}"
    cached = get_cached(key)
    if cached is not None:
        return cached
    result = fetch_trends_data(keyword, timeframe, geo)
    set_cached(key, result)
    return result


def cached_serper(query: str):
    key = f"serper::{query}"
    cached = get_cached(key)
    if cached is not None:
        return cached
    result = fetch_serper_data(query)
    set_cached(key, result)
    return result


def cached_reddit(keyword: str):
    key = f"reddit::{keyword}"
    cached = get_cached(key)
    if cached is not None:
        return cached
    result = fetch_reddit_complaints(keyword)
    set_cached(key, result)
    return result


def clear_all_caches():
    clear_all()
    st.cache_data.clear()
