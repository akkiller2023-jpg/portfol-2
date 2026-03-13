import http.server
import socketserver
import json
import os
import base64
import time

PORT = 8000
DATA_FILE = 'data.json'
TEMPLATE_FILE = 'template.html'
OUT_FILE = 'index.html'

def generate_static_site():
    """Reads data.json and injects it into template.html to produce index.html"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
            html = f.read()

        # --- Inject Single Values ---
        html = html.replace('{{ THEME_PRIMARY }}', data['theme']['primary'])
        html = html.replace('{{ THEME_ACCENT }}', data['theme']['accent'])
        html = html.replace('{{ HERO_TITLE }}', data['hero']['title'])
        html = html.replace('{{ HERO_SUBTITLE }}', data['hero']['subtitle'])
        html = html.replace('{{ HERO_IMAGE }}', data['hero']['image'])
        html = html.replace('{{ ABOUT_TEXT }}', data['about']['text'])

        # --- Inject Arrays (Hero Tags) ---
        tags_html = "".join([f'<div class="sht">{tag}</div>' for tag in data['hero']['skills']])
        html = html.replace('{{ HERO_TAGS_HTML }}', tags_html)

        # --- Inject Arrays (Skills) ---
        skills_html = ""
        delays = ['.15s', '.24s', '.32s', '.4s', '.5s', '.6s']
        for i, sk in enumerate(data['about']['skills']):
            d = delays[i] if i < len(delays) else '.5s'
            skills_html += f"""
            <div class="sk" data-rev="up" style="--d:{d}" onmouseenter="enter()" onmouseleave="leave()">
              <div class="sk-n">{sk['name']}</div>
              <div class="sk-d">{sk['desc']}</div>
              <div class="sk-bar-wrap"><div class="sk-pct">{sk['progress']}%</div><div class="sk-bg"><div class="sk-bar" data-p="{sk['progress']}" style="width:{sk['progress']}%;"></div></div></div>
            </div>
            """
        html = html.replace('{{ SKILLS_HTML }}', skills_html)

        # --- Inject Arrays (Projects) ---
        projects_html = ""
        for i, p in enumerate(data['projects']):
            tags_str = ' &middot; '.join(p['tags'])
            projects_html += f"""
            <a href="#" class="pcard tilt" data-rev="up" style="grid-column: 1 / -1; display: grid; grid-template-columns: 1fr 1fr; gap: 0; align-items: stretch; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.4); overflow: hidden; position: relative;" onmouseenter="enter()" onmouseleave="leave()">
              <div style="position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(circle at center, rgba(255, 255, 255, 0.05), transparent 60%); z-index: 0; pointer-events: none; animation: spin 20s linear infinite;"></div>
              
              <div class="pthumb" style="background:linear-gradient(to right, #111, #222); border-radius: 0; border: none; padding: 2rem; display:flex; justify-content:center; align-items:center; overflow:hidden; position:relative; z-index: 1;">
                <img src="{p['image']}" alt="{p['company']}" style="width: 80%; height: auto; max-height: 100%; object-fit: contain; transform: scale(1.05) translateZ(30px); filter: drop-shadow(0 20px 30px rgba(0,0,0,0.15)); transition: transform 0.6s cubic-bezier(0.2, 0.8, 0.2, 1);" class="hover-scale-img">
              </div>
              
              <div class="pb" style="background: rgba(10,10,15,0.6); border-radius: 0; border: none; border-left: 1px solid rgba(255, 255, 255, 0.05); padding: 3rem; display: flex; flex-direction: column; justify-content: center; z-index: 1; transform: translateZ(20px);">
                <span class="ptag" style="align-self: flex-start; margin-bottom: 1rem; font-size: 0.75rem; padding: 0.5rem 1rem;">{tags_str}</span>
                <div class="pt" style="font-size: 2.5rem; margin-bottom: 1rem;">{p['company']}</div>
                <div class="pd" style="font-size: 1.1rem; line-height: 1.6; margin-bottom: 2rem;"><b>{p['role']}</b><br><br>{p['description']}</div>
                <span class="pa" style="font-size: 1rem;">View Details &rarr;</span>
              </div>
            </a>
            """
        html = html.replace('{{ PROJECTS_HTML }}', projects_html)

        # --- Inject Arrays (Creatives) ---
        creatives_html = ""
        for c in data['creatives']:
            creatives_html += f"""
            <div class="cr-card tilt magic-hover" onmouseenter="enter()" onmouseleave="leave()">
              <img src="{c['image']}" alt="{c['title']}">
              <div class="cr-info"><div class="cr-t">{c['title']}</div><div class="cr-sub">{c['subtitle']}</div></div>
            </div>
            """
        # Duplicate for infinite scroll
        html = html.replace('{{ CREATIVES_HTML }}', creatives_html + creatives_html)

        # Write to index.html
        with open(OUT_FILE, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return True
    except Exception as e:
        print("SSG Error:", e)
        return False


class CMSHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/save':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                # 1. Parse incoming JSON
                data = json.loads(post_data.decode('utf-8'))
                
                # 2. Save pure JSON to data.json
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                
                # 3. Trigger SSG Build
                success = generate_static_site()
                
                if success:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'success': True}).encode())
                else:
                    self.send_response(500)
                    self.end_headers()
            except Exception as e:
                print("Error saving:", e)
                self.send_response(500)
                self.end_headers()

        elif self.path == '/api/upload':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                img_data = data['image'].split(',')[1]
                ext = data['ext']
                
                os.makedirs('assets', exist_ok=True)
                filename = f"upload_{int(time.time())}.{ext}"
                filepath = os.path.join('assets', filename)
                
                with open(filepath, "wb") as fh:
                    fh.write(base64.b64decode(img_data))
                    
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True, 'filePath': "assets/" + filename}).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()

    def do_GET(self):
        if self.path == '/api/data':
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(data.encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
        elif self.path == '/' or self.path == '':
            self.path = '/index.html'
            super().do_GET()
        elif self.path == '/admin' or self.path == '/admin/':
            self.path = '/admin/index.html'
            super().do_GET()
        else:
            # Fallback to normal HTTP hosting
            super().do_GET()


print("=========================================================")
print(f"Python WordPress CMS Started!")
print(f"Live Website:   http://localhost:{PORT}")
print(f"Admin Panel:    http://localhost:{PORT}/admin/index.html")
print("=========================================================")

with socketserver.TCPServer(("", PORT), CMSHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
