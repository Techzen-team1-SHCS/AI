import requests
import json
import re
import csv
import time


def generate_hotel_search_url(location, check_in, check_out, adults, api_key):
    base_url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_hotels",
        "q": location.replace(" ", "+"),
        "check_in_date": check_in,
        "check_out_date": check_out,
        "adults": str(adults),
        "currency": "VND",
        "gl": "vn",
        "hl": "vi",
        "api_key": api_key
    }
    query_string = "&".join(f"{key}={value}" for key, value in params.items())
    return f"{base_url}?{query_string}"


def fetch_and_process_json(url, location):
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        properties = data.get("properties", [])
        if not properties:
            print(f"Không tìm thấy dữ liệu khách sạn cho {location}.")
            return []

        hotels_list = []
        for hotel in properties:
            name = hotel.get("name", "Không có tên")
            description = hotel.get("description", "Không có mô tả")
            link = hotel.get("link", "Không có link")

            pricePerNight = 0
            rate_per_night = hotel.get("rate_per_night", {})
            lowest = rate_per_night.get("lowest")

            checknight = False
            if lowest:
                lowest_cleaned = re.sub(r"[^0-9]", "", lowest)
                if lowest_cleaned:
                    pricePerNight = int(lowest_cleaned)
                    checknight = True

            pricerate = 0
            total_rate = hotel.get("total_rate", {})
            lower = total_rate.get("lowest")
            if lower:
                lower_cleaned = re.sub(r"[^0-9]", "", lower)
                if lower_cleaned:
                    pricerate = int(lower_cleaned)

            price = str(pricePerNight if checknight else pricerate)

            name_nearby_place = ", ".join([near.get("name", "Không có tên") for near in hotel.get("nearby_places", [])])
            img_origin = ", ".join([img.get("original_image", "Không có ảnh") for img in hotel.get("images", [])])
            hotel_class = hotel.get("hotel_class", "Không có hạng sao")
            location_rating = hotel.get("location_rating", "Không có đánh giá vị trí")
            amenities = ", ".join(hotel.get("amenities", []))

            hotels_list.append([
                location, name, link, description, price, name_nearby_place,
                hotel_class, img_origin, location_rating, amenities
            ])

        return hotels_list
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi lấy dữ liệu cho {location}: {e}")
        return []


api_key = "5ab0507bc446a76ef1d8c27dff832452569a04fc1b0de2d82e4bbf4d5e9de31f"
provinces = [
    "An Giang", "Bà Rịa - Vũng Tàu", "Bắc Giang", "Bắc Kạn", "Bạc Liêu", "Bắc Ninh", "Bến Tre", "Bình Định",
    "Bình Dương", "Bình Phước", "Bình Thuận", "Cà Mau", "Cần Thơ", "Cao Bằng", "Đà Nẵng", "Đắk Lắk", "Đắk Nông",
    "Điện Biên", "Đồng Nai", "Đồng Tháp", "Gia Lai", "Hà Giang", "Hà Nam", "Hà Nội", "Hà Tĩnh", "Hải Dương",
    "Hải Phòng", "Hậu Giang", "Hòa Bình", "Hưng Yên", "Khánh Hòa", "Kiên Giang", "Kon Tum", "Lai Châu", "Lâm Đồng",
    "Lạng Sơn", "Lào Cai", "Long An", "Nam Định", "Nghệ An", "Ninh Bình", "Ninh Thuận", "Phú Thọ", "Phú Yên",
    "Quảng Bình", "Quảng Nam", "Quảng Ngãi", "Quảng Ninh", "Quảng Trị", "Sóc Trăng", "Sơn La", "Tây Ninh",
    "Thái Bình", "Thái Nguyên", "Thanh Hóa", "Thừa Thiên Huế", "Tiền Giang", "TP. Hồ Chí Minh", "Trà Vinh",
    "Tuyên Quang", "Vĩnh Long", "Vĩnh Phúc", "Yên Bái"
]

check_in = "2025-04-10"
check_out = "2025-04-11"
adults = 3
output_file = "all_hotels.csv"

all_hotels = []
for province in provinces:
    search_url = generate_hotel_search_url(province, check_in, check_out, adults, api_key)
    print(f"Đang lấy dữ liệu khách sạn cho: {province}")
    hotels = fetch_and_process_json(search_url, province)
    all_hotels.extend(hotels)
    time.sleep(2)  # Tránh bị giới hạn APIy

with open(output_file, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow([
        "name", "link", "description", "price", "name_nearby_place",
        "hotel_class", "img_origin", "location_rating", "location"
    ])
    writer.writerows(all_hotels)

print(f"Dữ liệu tất cả các tỉnh đã được lưu vào {output_file}")
