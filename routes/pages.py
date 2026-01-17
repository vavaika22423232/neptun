# Pages routes - Static pages, SEO pages, web frontend
# Extracted from app.py for better code organization

import os
import logging
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, send_from_directory, jsonify

from .config import get_kyiv_now

log = logging.getLogger(__name__)

# Create blueprint
pages_bp = Blueprint('pages', __name__)

# =============================================================================
# STATIC FILES & SEO
# =============================================================================
@pages_bp.route('/google2848d36b38653ede.html')
def google_verification():
    """Google Search Console verification file."""
    return 'google-site-verification: google2848d36b38653ede.html'


@pages_bp.route('/ads.txt')
def ads_txt():
    """AdSense ads.txt file."""
    return send_from_directory('.', 'ads.txt', mimetype='text/plain')


@pages_bp.route('/app-ads.txt')
def app_ads_txt():
    """App ads.txt for mobile apps."""
    return send_from_directory('.', 'app-ads.txt', mimetype='text/plain')


@pages_bp.route('/robots.txt')
def robots_txt():
    """Robots.txt for search engines."""
    content = """User-agent: *
Allow: /
Disallow: /admin
Disallow: /api/

Sitemap: https://neptun.in.ua/sitemap.xml
"""
    return content, 200, {'Content-Type': 'text/plain'}


@pages_bp.route('/sitemap.xml')
def sitemap():
    """XML sitemap for SEO."""
    now = get_kyiv_now().strftime('%Y-%m-%d')
    
    pages = [
        ('/', '1.0', 'daily'),
        ('/about', '0.8', 'weekly'),
        ('/faq', '0.7', 'weekly'),
        ('/privacy', '0.5', 'monthly'),
        ('/terms', '0.5', 'monthly'),
        ('/contact', '0.6', 'monthly'),
        ('/community', '0.7', 'weekly'),
        ('/news', '0.8', 'daily'),
    ]
    
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    for url, priority, changefreq in pages:
        xml += f'''  <url>
    <loc>https://neptun.in.ua{url}</loc>
    <lastmod>{now}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>\n'''
    
    xml += '</urlset>'
    
    return xml, 200, {'Content-Type': 'application/xml'}


# =============================================================================
# ICON ROUTES
# =============================================================================
@pages_bp.route('/icon_missile.svg')
def icon_missile():
    """Missile icon SVG."""
    return send_from_directory('static', 'icon_missile.svg', mimetype='image/svg+xml')


@pages_bp.route('/icon_balistic.svg')
def icon_balistic():
    """Ballistic icon SVG."""
    return send_from_directory('static', 'icon_balistic.svg', mimetype='image/svg+xml')


@pages_bp.route('/icon_drone.svg')
def icon_drone():
    """Drone icon SVG."""
    return send_from_directory('static', 'icon_drone.svg', mimetype='image/svg+xml')


@pages_bp.route('/favicon.ico')
def favicon():
    """Favicon."""
    return send_from_directory('static', 'favicon.ico', mimetype='image/x-icon')


# =============================================================================
# MAIN PAGES
# =============================================================================
@pages_bp.route('/')
def index():
    """Main page."""
    return render_template('index_index.html')


@pages_bp.route('/new')
def index_new():
    """New design page."""
    return render_template('index_index.html')


@pages_bp.route('/old')
def index_old():
    """Old design page."""
    return render_template('index_index.html')


@pages_bp.route('/shahed-map')
@pages_bp.route('/shahed')
@pages_bp.route('/drones')
def shahed_map():
    """Drone/Shahed tracking map."""
    return render_template('shahed_map.html')


@pages_bp.route('/region/<region_slug>')
def region_page(region_slug):
    """Region-specific page for SEO."""
    return render_template('region.html', region=region_slug)


@pages_bp.route('/map-only')
def map_only():
    """Map-only view (no UI)."""
    return render_template('map_only.html')


@pages_bp.route('/map-old')
def map_old():
    """Old map design."""
    return render_template('index_map.html')


@pages_bp.route('/map-embed')
def map_embed():
    """Embeddable map."""
    return render_template('index_map.html')


@pages_bp.route('/svg')
def svg_page():
    """SVG assets page."""
    return render_template('index_index.html')


@pages_bp.route('/about')
def about():
    """About page."""
    return render_template('index_index.html')


@pages_bp.route('/analytics')
def analytics():
    """Analytics page."""
    return render_template('analytics.html')


# =============================================================================
# COMMUNITY / SOCIAL REDIRECTS
# =============================================================================
@pages_bp.route('/community')
@pages_bp.route('/telegram')
@pages_bp.route('/join')
def community():
    """Redirect to Telegram community."""
    return redirect('https://t.me/neptun_in_ua')


@pages_bp.route('/channel')
@pages_bp.route('/group')
@pages_bp.route('/chat')
def telegram_channel():
    """Redirect to Telegram channel."""
    return redirect('https://t.me/neptun_in_ua')


@pages_bp.route('/news')
@pages_bp.route('/updates')
@pages_bp.route('/alerts')
def news():
    """Redirect to news/alerts channel."""
    return redirect('https://t.me/neptun_in_ua')


# =============================================================================
# INFO PAGES
# =============================================================================
@pages_bp.route('/faq')
def faq():
    """FAQ page."""
    return render_template('index_index.html')


@pages_bp.route('/privacy')
def privacy():
    """Privacy policy page."""
    return render_template('privacy.html')


@pages_bp.route('/terms')
def terms():
    """Terms of service page."""
    return render_template('privacy.html')  # Same template as privacy


@pages_bp.route('/contact')
def contact():
    """Contact page."""
    return render_template('index_index.html')


# =============================================================================
# LOCATION SERVICE
# =============================================================================
@pages_bp.route('/locate')
def locate():
    """Location service page."""
    return render_template('index_index.html')


# =============================================================================
# MISC PAGES
# =============================================================================
@pages_bp.route('/channels')
def channels():
    """Telegram channels list."""
    return render_template('index_index.html')


@pages_bp.route('/data')
def data_page():
    """Data explorer page."""
    return render_template('index_index.html')


@pages_bp.route('/active_alarms')
def active_alarms():
    """Active alarms display page."""
    return render_template('index_index.html')


@pages_bp.route('/alarms_stats')
def alarms_stats():
    """Alarm statistics page."""
    return render_template('analytics.html')


@pages_bp.route('/comments', methods=['GET', 'POST'])
def comments():
    """Comments page."""
    return render_template('index_index.html')


# =============================================================================
# HEALTH & STATUS
# =============================================================================
@pages_bp.route('/healthz')
def healthz():
    """Health check endpoint for load balancers."""
    return jsonify({'status': 'ok', 'timestamp': get_kyiv_now().isoformat()})


@pages_bp.route('/version')
def version():
    """Version endpoint."""
    return jsonify({
        'version': '2.0.0',
        'service': 'neptun-alarm-api',
        'timestamp': get_kyiv_now().isoformat()
    })


@pages_bp.route('/startup_diag')
def startup_diagnostics():
    """Startup diagnostics."""
    return jsonify({
        'status': 'running',
        'timestamp': get_kyiv_now().isoformat()
    })


@pages_bp.route('/api/cache-stats')
def cache_stats():
    """Cache statistics."""
    from .config import RESPONSE_CACHE
    return jsonify(RESPONSE_CACHE.stats())
