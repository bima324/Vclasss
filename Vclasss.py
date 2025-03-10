import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import time

# Load credentials dari .env
load_dotenv()
USERNAME = os.getenv("VCLASS_USERNAME")
PASSWORD = os.getenv("VCLASS_PASSWORD")

# URL V-Class Gunadarma
LOGIN_URL = "https://v-class.gunadarma.ac.id/login/index.php"
DASHBOARD_URL = "https://v-class.gunadarma.ac.id/my/"
TIMELINE_URL = "https://v-class.gunadarma.ac.id/my/"

# Session untuk menyimpan cookies
session = requests.Session()

def make_request_with_retry(url, retries=3, delay=5):
    """Mencoba request dengan retry mechanism."""
    for attempt in range(retries):
        try:
            response = session.get(url)
            response.raise_for_status()  # Akan raise exception jika status code 4xx/5xx
            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ Error pada request ke {url}: {e}")
            if attempt < retries - 1:
                print(f"⏳ Mencoba ulang dalam {delay} detik...")
                time.sleep(delay)
            else:
                print(f"❌ Gagal setelah {retries} kali percobaan.")
                return None

def make_request_with_backoff(url, retries=5, initial_delay=1):
    """Mencoba request dengan exponential backoff."""
    delay = initial_delay
    for attempt in range(retries):
        try:
            response = session.get(url)
            response.raise_for_status()  # Akan raise exception jika status code 4xx/5xx
            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ Error pada request ke {url}: {e}")
            if attempt < retries - 1:
                print(f"⏳ Mencoba ulang dalam {delay} detik...")
                time.sleep(delay)
                delay *= 2  # Jeda bertambah setiap gagal
            else:
                print(f"❌ Gagal setelah {retries} kali percobaan.")
                return None

def server_down_options(url):
    """Menampilkan opsi alternatif saat server down."""
    print("\n⚠️ Server sedang mengalami gangguan atau down. Pilih salah satu opsi untuk mencoba mengakses lagi:")
    print("1. Coba lagi dengan retry (5 kali percobaan)")
    print("2. Coba lagi dengan exponential backoff (5 kali percobaan)")
    print("3. Gunakan proxy untuk mencoba akses")

    choice = input("Pilih opsi (1/2/3): ")

    if choice == '1':
        print("⏳ Mencoba lagi dengan retry...")
        response = make_request_with_retry(url)
    elif choice == '2':
        print("⏳ Mencoba lagi dengan exponential backoff...")
        response = make_request_with_backoff(url)
    elif choice == '3':
        proxy = input("Masukkan alamat proxy (contoh: http://proxyserver:port): ")
        proxies = {"http": proxy, "https": proxy}
        try:
            response = requests.get(url, proxies=proxies)
            if response.status_code == 200:
                print("✅ Berhasil mengakses dengan proxy!")
            else:
                print(f"❌ Gagal mengakses dengan proxy, status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Error saat mencoba proxy: {e}")
            response = None
    else:
        print("❌ Pilihan tidak valid, kembali ke menu utama.")
        response = None

    if response:
        print("✅ Berhasil mendapatkan data!")
    else:
        print("❌ Gagal mengakses data. Silakan coba lagi nanti.")

def login():
    """Melakukan login ke V-Class"""
    response = make_request_with_retry(LOGIN_URL)
    if not response:
        print("❌ Gagal mengakses halaman login, coba opsi alternatif.")
        server_down_options(LOGIN_URL)
        return False

    soup = BeautifulSoup(response.text, "html.parser")

    # Ambil token login
    logintoken = soup.find("input", {"name": "logintoken"})
    logintoken = logintoken["value"] if logintoken else ""
    print(f"🔑 Mencari token login... {logintoken}")

    # Data login
    payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "logintoken": logintoken
    }

    try:
        login_response = session.post(LOGIN_URL, data=payload)
        login_response.raise_for_status()  # Akan menimbulkan error jika status code 4xx/5xx
    except requests.exceptions.RequestException as e:
        print(f"❌ Kesalahan saat login: {e}")
        return False

    if "loginerrors" in login_response.text:
        print("❌ Login gagal! Periksa username/password Anda.")
        return False
    
    print("✅ Login Berhasil! Selamat datang di V-Class! 🎉")
    return True

def get_courses(filter_name=None):
    """Mengambil daftar mata kuliah dari dashboard, bisa filter nama dosen"""
    response = make_request_with_retry(DASHBOARD_URL)
    if not response:
        print("❌ Gagal mengambil data mata kuliah.")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    courses = soup.select("ul.unlist li div.column a")
    course_list = []

    print("\n📚 Daftar Mata Kuliah Tersedia 📚")
    for course in courses:
        title = course.get_text(strip=True)
        link = course["href"]
        # Filter berdasarkan nama dosen
        if filter_name and filter_name.lower() not in title.lower():
            continue
        course_list.append({"title": title, "link": link})
        print(f"  ➡️ {title} → {link}")

    time.sleep(1)  # Menambahkan sedikit jeda antar permintaan
    return course_list

def get_course_detail(course_link):
    """Menampilkan detail dari mata kuliah yang dipilih"""
    response = make_request_with_retry(course_link)
    if not response:
        print("❌ Gagal mengambil detail mata kuliah.")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    description = soup.select_one("div#intro")
    if description:
        print(f"\n🎓 Detail Mata Kuliah:\n{description.get_text(strip=True)}")
    else:
        print("❌ Detail mata kuliah tidak ditemukan.")

def get_timeline():
    """Mengambil aktivitas terbaru dari timeline"""
    response = make_request_with_retry(TIMELINE_URL)
    if not response:
        print("❌ Gagal mengambil data aktivitas.")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    activities = soup.select("div.activityinstance a")
    timeline = []

    if not activities:
        print("\n✨ Tidak ada tugas atau aktivitas terbaru untuk hari ini. Nikmati waktumu! ✨")
        return []

    print("\n📝 Aktivitas Terbaru 📝")
    for activity in activities:
        activity_title = activity.get_text(strip=True)
        activity_link = activity["href"]
        deadline = activity.find_next("span", class_="due_date")  # Pastikan ada elemen untuk deadline
        course_name = activity.find_previous("div", class_="course_name")  # Menyesuaikan berdasarkan struktur HTML yang ada

        # Keterangan jika ada deadline
        if deadline:
            print(f"  ➡️ {activity_title} - {course_name.get_text(strip=True)} (Deadline: {deadline.get_text(strip=True)}) → {activity_link}")
        else:
            print(f"  ➡️ {activity_title} - {course_name.get_text(strip=True)} → {activity_link}")

    time.sleep(1)  # Menambahkan sedikit jeda antar permintaan
    return timeline

def get_calendar():
    """Mengambil kalender dan event-event terkait"""
    print("\n📅 Kalender Tidak Tersedia 📅")
    print("Tidak ada event atau tanggal yang ditemukan.")

# Fungsi untuk menampilkan menu utama
def main_menu():
    """Menampilkan menu utama dan menangani pilihan"""
    while True:
        print("\n===== Menu Utama =====")
        print("1. Daftar Mata Kuliah 📖 (Tampilkan semua mata kuliah)")
        print("2. Daftar Mata Kuliah Berdasarkan Dosen 📚 (Masukkan nama dosen)")
        print("3. Aktivitas Terbaru 📝")
        print("4. Kalender 📅")
        print("5. Keluar 👋")

        choice = input("Pilih opsi (1/2/3/4/5): ")

        if choice == '1':
            courses = get_courses()
            if courses:
                while True:
                    choice_course = input("Pilih mata kuliah untuk melihat detail (masukkan nomor atau 0 untuk kembali): ")
                    if choice_course == '0':
                        break
                    try:
                        choice_course = int(choice_course)
                        if 1 <= choice_course <= len(courses):
                            get_course_detail(courses[choice_course - 1]['link'])
                        else:
                            print("❌ Nomor mata kuliah tidak valid. Silakan pilih nomor yang ada.")
                    except ValueError:
                        print("❌ Input tidak valid. Masukkan nomor mata kuliah yang benar.")

        elif choice == '2':
            filter_name = input("Masukkan nama dosen untuk filter (kosongkan untuk semua): ")
            courses = get_courses(filter_name=filter_name)
            if courses:
                while True:
                    choice_course = input("Pilih mata kuliah untuk melihat detail (masukkan nomor atau 0 untuk kembali): ")
                    if choice_course == '0':
                        break
                    try:
                        choice_course = int(choice_course)
                        if 1 <= choice_course <= len(courses):
                            get_course_detail(courses[choice_course - 1]['link'])
                        else:
                            print("❌ Nomor mata kuliah tidak valid. Silakan pilih nomor yang ada.")
                    except ValueError:
                        print("❌ Input tidak valid. Masukkan nomor mata kuliah yang benar.")

        elif choice == '3':
            get_timeline()

        elif choice == '4':
            get_calendar()

        elif choice == '5':
            print("👋 Terima kasih telah menggunakan V-Class bot! Sampai jumpa!")
            break
        else:
            print("❌ Pilihan tidak valid. Silakan pilih opsi yang tersedia.")

# Jalankan program
if __name__ == "__main__":
    if login():
        main_menu()
    else:
        print("❌ Login gagal, program akan keluar.")
