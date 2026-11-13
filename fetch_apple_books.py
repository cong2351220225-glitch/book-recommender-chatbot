import requests
import pandas as pd
import uuid
import os
import time
import re

# Thêm rất nhiều từ khóa để cào được 200+ sách
KEYWORDS = [
    "tâm lý", "kinh doanh", "phát triển bản thân", "tiểu thuyết", 
    "khoa học", "kỹ năng sống", "lịch sử", "văn học việt nam", 
    "sức khỏe", "tài chính", "khởi nghiệp", "marketing", "triết học"
]
MAX_RESULTS_PER_KEYWORD = 30 # Tải 30 cuốn cho mỗi chủ đề

BOOKS_CSV_PATH = "data/books.csv"

def strip_html(text):
    """Xóa các thẻ HTML rác thường có trong mô tả của Apple Books"""
    if not text: return "Cuốn sách này hiện chưa có tóm tắt chi tiết."
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text).strip()

def fetch_books_from_apple():
    new_books = []
    print("🚀 Bắt đầu tải sách tiếng Việt từ Apple Books (Không giới hạn IP)...")
    
    for keyword in KEYWORDS:
        print(f"⏳ Đang tìm chủ đề: {keyword}...")
        # API của Apple Books chuyên dành cho Ebook tại thị trường VN
        url = f"https://itunes.apple.com/search?term={keyword}&media=ebook&country=vn&limit={MAX_RESULTS_PER_KEYWORD}"
        
        try:
            response = requests.get(url)
            data = response.json()
            
            if "results" not in data or len(data["results"]) == 0:
                print(f"  ⚠️ Không tìm thấy sách cho '{keyword}'.")
                continue
                
            for item in data["results"]:
                title = item.get("trackName", "Không rõ tên")
                author = item.get("artistName", "Không rõ tác giả")
                
                # Apple Books có mô tả rất dài và hay, phù hợp cho AI RAG
                raw_description = item.get("description", "")
                description = strip_html(raw_description)
                
                # Nâng cấp chất lượng ảnh bìa từ 100px lên 600px sắc nét
                cover_url = item.get("artworkUrl100", "").replace("100x100bb", "600x600bb")
                
                year = item.get("releaseDate", "2020")[:4]
                
                # Lấy thể loại gốc của Apple nếu có
                genres = item.get("genres", [keyword.title()])
                primary_genre = genres[0] if genres else keyword.title()
                
                new_books.append({
                    "book_id": str(uuid.uuid4())[:8],
                    "title": title,
                    "author": author,
                    "genre": primary_genre,
                    "year": year,
                    "rating": item.get("averageUserRating", 4.5), # Rating thực tế của Apple
                    "summary": description[:500] + "..." if len(description) > 500 else description,
                    "description": description,
                    "cover_url": cover_url,
                    "language": "Tiếng Việt",
                    "pages": 250,
                    "format": "Ebook",
                    "target_audience": "Mọi độc giả",
                    "difficulty": "Trung bình",
                    "mood": "Tích cực",
                    "featured": False,
                    "purchase_url": item.get("trackViewUrl", ""), # Link mua thật trên Apple Books
                    "reading_available": False,
                    "reading_url": "",
                    "local_file": "",
                    "tags": keyword
                })
                
            print(f"  ✅ Đã lấy xong {len(data['results'])} cuốn cho chủ đề '{keyword}'")
            time.sleep(1) # Nghỉ nhẹ 1 giây cho máy chủ Apple vui vẻ
            
        except Exception as e:
            print(f"❌ Lỗi khi tải {keyword}: {e}")
            
    return new_books

def append_to_csv(new_books):
    if not os.path.exists(BOOKS_CSV_PATH):
        print("❌ Không tìm thấy file data/books.csv!")
        return
        
    df_old = pd.read_csv(BOOKS_CSV_PATH)
    df_new = pd.DataFrame(new_books)
    
    if df_new.empty:
        print("⚠️ Không có cuốn sách nào được tải về.")
        return
        
    # Gộp sách cũ và mới, loại bỏ các sách trùng tên để dữ liệu sạch đẹp
    df_combined = pd.concat([df_old, df_new], ignore_index=True)
    df_combined = df_combined.drop_duplicates(subset=["title"], keep="first")
    
    # Lưu lại vào file
    df_combined.to_csv(BOOKS_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"\n🎉 ĐÃ LƯU THÀNH CÔNG! Kho sách của bạn hiện có tổng cộng: {len(df_combined)} cuốn.")

if __name__ == "__main__":
    fetched_books = fetch_books_from_apple()
    append_to_csv(fetched_books)