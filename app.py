from flask import Flask, render_template, session, request, redirect, url_for, flash
import mysql.connector
from werkzeug.security import generate_password_hash
import bcrypt
import os
from datetime import datetime, timedelta, time
from mysql.connector import Error




# Flask 애플리케이션 객체 생성
app = Flask(__name__)
# secret_key 설정 (세션 관련 문제 해결)
app.secret_key = os.urandom(24)
# 세션 유효시간 30분 설정
app.permanent_session_lifetime = timedelta(minutes=30)  

########################################################################################
# MySQL 연결 설정
def get_db_connection():
    return mysql.connector.connect(
        host='127.0.0.1',
        user='root',
        password=os.getenv('MYSQL_PASSWORD'),  #.evn에 입력
        database='rentcar'
    )
########################################################################################
########################################################################################
########################################################################################
# 홈페이지 라우팅 (HTML 페이지 렌더링)
@app.route('/')
def home():
    # 로그인 상태 확인
    user_logged_in = 'user_id' in session
    name = session.get('name', '')  # 세션에서 사용자 이름 가져오기

    return render_template('home.html', user_logged_in=user_logged_in, name=name)
#####################################################
# 회원가입 페이지
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']

        # 비밀번호 해싱
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # MySQL에 사용자 정보 저장 (customer 테이블에 저장)
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (role, password, name, email, phone) VALUES (%s, %s, %s, %s, %s)", 
                           ('customer', hashed_password, name, email, phone))
            
            conn.commit()
            flash('회원가입이 완료되었습니다!', 'success')
            return redirect('/login')
        except mysql.connector.Error as err:
            flash(f"Error: {err}", 'danger')
            return render_template('signup.html')
        finally:
            cursor.close()
            conn.close()

    return render_template('signup.html')

# 로그인 페이지
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection() #DB 연결 함수
        cursor = conn.cursor(dictionary=True)

        # 이메일로 사용자 정보 조회
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            # 로그인 성공 시 세션에 사용자 정보 저장
            session['user_id'] = user['user_id']
            session['email'] = user['email']
            session['name'] = user['name']
            session['role'] = user['role']  # 'admin' 또는 'customer'
            flash('로그인 성공!', 'success')

            # 관리자라면 관리자 대시보드로 리다이렉트
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            
            return redirect(url_for('home'))  # 로그인 후 홈 페이지로 리다이렉트
        else:
            flash('이메일이나 비밀번호가 잘못되었습니다.', 'danger')

    return render_template('login.html')

# 로그아웃
@app.route('/logout')
def logout():
    # 세션 종료
    session.pop('user_id', None)  # 세션에서 사용자 정보 제거
    # 쿠키 삭제 (브라우저에서 직접 만료시켜서 삭제)
    session.clear()
    
    # 로그아웃 후 캐시 방지 설정
    response = redirect(url_for('login'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response















###########################################################################################################
###########################################################################################################
###########################################################################################################
###########################################################################################################
###########################################################################################################

#####관리자 페이지######

# 관리자 대시보드 페이지 (로그인 후 접근)
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('관리자만 접근 가능합니다.', 'warning')
        return redirect(url_for('login'))  # 관리자만 접근 가능하도록 설정

    return render_template('admin_dashboard.html')  # 관리자 대시보드 페이지로 이동


#관리자 예약관리 페이지
@app.route('/admin/reservation', methods=['GET', 'POST'])
def admin_reservations():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('관리자만 접근 가능합니다.', 'warning')
        return redirect(url_for('login'))  # 관리자만 접근 가능하도록 설정
    
    # MySQL 연결
    connection = get_db_connection()
    cursor = connection.cursor()

    # 삭제 요청 처리
    if request.method == 'POST' and 'delete_reservation_id' in request.form:
        reservation_id_to_delete = request.form['delete_reservation_id']

        # 예약 삭제 쿼리
        delete_query = """
            DELETE FROM reservation
            WHERE reservation_id = %s
        """
        cursor.execute(delete_query, (reservation_id_to_delete,))
        connection.commit()  # 변경 사항 저장
        flash('예약이 삭제되었습니다.', 'success')
    

    # 사용자가 검색한 조건 받아오기
    search_query = request.form.get('search')  # 이름, 전화번호, 픽업 날짜
    pickup_date = request.form.get('pickup_date')  # 픽업 날짜 검색

    if request.method == 'POST':
        # 예약의 확인 직원 이름을 수정하는 처리
        for reservation in request.form:
            if reservation.startswith('employee_name_'):
                reservation_id = reservation.split('_')[2]  # 예약 ID 추출
                employee_name = request.form[reservation]  # 수정된 직원 이름

                # 데이터베이스에 수정된 이름을 반영하는 쿼리
                update_query = """
                    UPDATE reservation
                    SET employee_name = %s
                    WHERE reservation_id = %s
                """
                cursor.execute(update_query, (employee_name, reservation_id))

        connection.commit()  # 변경 사항 저장
        flash('확인 직원 이름이 수정되었습니다.', 'success')


    if search_query or pickup_date:
        # 사용자 검색어 또는 픽업 날짜로 검색
        if pickup_date:
            # 픽업 날짜로 검색
            query = """
                SELECT r.reservation_id, r.user_id, u.name AS user_name, r.car_id, r.start_date, r.end_date, r.pickup_time, r.return_time,r.employee_name, u.phone
                FROM reservation r
                JOIN users u ON r.user_id = u.user_id
                WHERE DATE(r.start_date) = %s
            """
            cursor.execute(query, (pickup_date,))
        else:
            # 이름이나 전화번호로 검색
            query = """
                SELECT r.reservation_id, r.user_id, u.name AS user_name, r.car_id, r.start_date, r.end_date, r.pickup_time, r.return_time,r.employee_name, u.phone
                FROM reservation r
                JOIN users u ON r.user_id = u.user_id
                WHERE u.name LIKE %s OR u.phone LIKE %s
            """
            cursor.execute(query, (f'%{search_query}%', f'%{search_query}%'))
    else:
        # 검색어가 없으면 모든 예약 조회
        query = """
            SELECT r.reservation_id, r.user_id, u.name AS user_name, r.car_id, r.start_date, r.end_date, r.pickup_time, r.return_time, r.employee_name, u.phone
            FROM reservation r
            JOIN users u ON r.user_id = u.user_id
        """
        
        cursor.execute(query)

    reservations = cursor.fetchall()
    cursor.close()
    connection.close()


    return render_template('admin/reservation.html', reservations=reservations)


############################
# 차량 관리 페이지
@app.route('/admin/car', methods=['GET'])
def cars():
    return render_template('admin/car.html')  # 차량 관리 페이지로 렌더링


# 관리자 자동차 등록(고유번호 부여 및 조회) 페이지
@app.route('/admin/add_car', methods=['GET', 'POST'])
def add_car():
    if request.method == 'POST':
        # 폼에서 받은 정보로 DB에 삽입
        car_name = request.form['car_name']
        model_year = request.form['model_year']
        color = request.form['color']
        

        # DB에 차량 정보 추가
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # cars 테이블에 자동차 추가
        query_cars = """
        INSERT INTO cars (car_name, model_year, color)
        VALUES (%s, %s, %s)
        """
        cursor.execute(query_cars, (car_name, model_year, color))
        connection.commit()

        cursor.close()
        connection.close()

        flash('자동차가 등록되었습니다.', 'success')

        # 차량 목록을 다시 로드하도록 리다이렉트
        return redirect('/admin/add_car')

    else:
        # 차량 목록 불러오기
        search_query = request.args.get('search', '')  # 검색어 받아오기
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        if search_query:
            # 검색어가 있으면 차량 이름 또는 ID로 검색
            query = """
            SELECT cars.car_id, cars.car_name, cars.model_year, cars.color, car.car_type, car.fuel_type,
                   (SELECT status FROM maintenance WHERE maintenance.car_id = cars.car_id AND status IN ('진행중', '대기') LIMIT 1) AS maintenance_status
            FROM cars
            LEFT JOIN car ON cars.car_name = car.car_name AND cars.model_year = car.model_year AND cars.color = car.color
            WHERE cars.car_name LIKE %s OR cars.car_id LIKE %s
            ORDER BY cars.car_name ASC, cars.car_id
            """
            cursor.execute(query, ('%' + search_query + '%', '%' + search_query + '%'))
        else:
            # 검색어가 없으면 모든 차량 목록을 반환
            query = """
            SELECT cars.car_id, cars.car_name, cars.model_year, cars.color, car.car_type, car.fuel_type, 
                (SELECT status FROM maintenance WHERE maintenance.car_id = cars.car_id AND status IN ('진행중', '대기') LIMIT 1) AS maintenance_status
            FROM cars
            LEFT JOIN car ON cars.car_name = car.car_name AND cars.model_year = car.model_year AND cars.color = car.color
            ORDER BY cars.car_name ASC, cars.car_id
            """
            cursor.execute(query)

        carsdata = cursor.fetchall()  # 결과 가져오기
        cursor.close()
        connection.close()

        return render_template('admin/add_car.html', carsdata=carsdata)
## 등록 자동차 삭제
@app.route('/admin/delete_car/<int:car_id>', methods=['POST'])
def delete_car(car_id):
    # 차량 삭제 처리
    connection = get_db_connection()
    cursor = connection.cursor()

    # maintenance 테이블에서 해당 차량의 유지보수 기록 삭제
    cursor.execute("DELETE FROM maintenance WHERE car_id = %s", (car_id,))
    
    # cars 테이블에서 해당 차량 삭제
    cursor.execute("DELETE FROM cars WHERE car_id = %s", (car_id,))
    
    connection.commit()
    cursor.close()
    connection.close()

    flash('차량이 삭제되었습니다.', 'danger')
    return redirect('/admin/add_car')


# 관리자 유지보수 페이지
@app.route('/admin/car_maintenance', methods=['GET', 'POST'])
def maintenance():
    if request.method == 'POST':
        car_id = request.form['car_id']
        maintenance_type = request.form['maintenance_type']
        status = request.form['status']

        
        # DB에 유지보수 정보 추가
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # car_id가 존재하는지 확인
        cursor.execute("SELECT COUNT(*) FROM cars WHERE car_id = %s", (car_id,))
        car_exists = cursor.fetchone()['COUNT(*)']

        if car_exists == 0:
            flash('유효하지 않은 자동차 ID입니다. 해당 ID는 존재하지 않습니다.', 'error')
            cursor.close()
            connection.close()
            return redirect('/admin/car_maintenance')


        query_maintenance = """
        INSERT INTO maintenance (car_id, maintenance_type, status)
        VALUES (%s, %s, %s)
        """
        cursor.execute(query_maintenance, (car_id, maintenance_type, status))
        connection.commit()

        cursor.close()
        connection.close()

        flash('자동차가 등록되었습니다.', 'success')

        # 차량 목록을 다시 로드하도록 리다이렉트
        return redirect('/admin/car_maintenance')

    else:
        search_car_id = request.args.get('car_id', '')
        search_maintenance_type = request.args.get('maintenance_type', '')
        search_status = request.args.get('status', '')

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
        SELECT * FROM maintenance WHERE 1=1
        """
        # 검색 필터 추가
        filters = []
        if search_car_id:
            query += " AND car_id LIKE %s"
            filters.append(f'%{search_car_id}%')
        if search_maintenance_type:
            query += " AND maintenance_type LIKE %s"
            filters.append(f'%{search_maintenance_type}%')
        if search_status:
            query += " AND status LIKE %s"
            filters.append(f'%{search_status}%')

        cursor.execute(query, tuple(filters))
        maintenance_data = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template('admin/car_maintenance.html', maintenance_data=maintenance_data)

# 유지보수 수정/삭제 처리
@app.route('/admin/update_maintenance', methods=['POST'])
def update_maintenance():
    maintenance_id = request.form['maintenance_id']
    maintenance_type = request.form['maintenance_type']
    status = request.form['status']
    cost = request.form['cost']
    maintenance_date = request.form['maintenance_date']
    employee_name = request.form['employee_name']
    details = request.form['details']

    # DB에서 해당 유지보수 정보 수정
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # 빈 문자열을 NULL로 처리
    if cost == '':
        cost = None

    update_query = """
    UPDATE maintenance
    SET maintenance_type = COALESCE(%s, maintenance_type),
        status = COALESCE(%s, status),
        cost = COALESCE(%s, cost),
        maintenance_date = COALESCE(%s, maintenance_date),
        employee_name = COALESCE(%s, employee_name),
        details = COALESCE(%s, details)
    WHERE maintenance_id = %s
    """
    cursor.execute(update_query, (maintenance_type, status, cost, maintenance_date,
                                  employee_name, details, maintenance_id))
    connection.commit()

    cursor.close()
    connection.close()

    flash('유지보수 정보가 수정되었습니다.', 'success')
    return redirect('/admin/car_maintenance')
@app.route('/admin/delete_maintenance/<int:maintenance_id>', methods=['GET'])
def delete_maintenance(maintenance_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # 유지보수 삭제
    delete_query = "DELETE FROM maintenance WHERE maintenance_id = %s"
    cursor.execute(delete_query, (maintenance_id,))
    connection.commit()

    cursor.close()
    connection.close()

    flash('유지보수 정보가 삭제되었습니다.', 'success')
    return redirect('/admin/car_maintenance')



#관리자 자동차 종류 페이지
@app.route('/admin/car_types', methods=['GET', 'POST'])
def car_types():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # 차량 등록 처리
    if request.method == 'POST' and 'search' not in request.form and 'delete_car' not in request.form:
        car_name = request.form['car_name']
        car_type = request.form['car_type']
        fuel_type = request.form['fuel_type']
        color = request.form['color']
        model_year = request.form['model_year']
        car_image = request.form['car_image']  # 이미지 URL

        # 차량 중복 여부 확인
        cursor.execute("SELECT * FROM car WHERE car_name = %s AND model_year = %s AND color = %s", (car_name, model_year, color))
        existing_car = cursor.fetchone()
        
        if existing_car:
            flash('이미 등록된 차량입니다.', 'error')
        else:
            # 차량 정보 등록
            car_query = """
                INSERT INTO car (car_name, model_year, color, car_type, fuel_type, image_url)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(car_query, (car_name, model_year, color, car_type, fuel_type, car_image))
            connection.commit()

    # 차량 삭제 처리
    if request.method == 'POST' and 'delete_car' in request.form:
        car_id_to_delete = request.form['delete_car']
    
        # 차량 ID를 받아서 해당 차량 삭제
        delete_query = "DELETE FROM car WHERE car_id = %s"
        cursor.execute(delete_query, (car_id_to_delete,))
        connection.commit()
    
        flash('차량이 삭제되었습니다.', 'success')
        return redirect('/admin/car_types')  # 삭제 후 새로고침

    # 차량 검색 처리
    search_query = request.args.get('search')  # GET 방식으로 검색어 가져오기
    if search_query:
        query = """
            SELECT *
            FROM car
            WHERE car_name LIKE %s
            ORDER BY car_name ASC
        """
        cursor.execute(query, ('%' + search_query + '%',))
    else:
        # 검색어가 없으면 모든 차량 조회
        query = """
            SELECT *
            FROM car
            ORDER BY car_name ASC
        """
        cursor.execute(query)

    cars = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template('admin/car_types.html', cars=cars)





















#################################################################################################
#################################################################################################
#################################################################################################
#################################################################################################
#################################################################################################

#####고객페이지#####

# 예약 페이지
@app.route('/reservation', methods=['GET', 'POST'])
def reservation():
    # 로그인 상태 확인
    user_logged_in = 'user_id' in session
    name = session.get('name', '')  # 세션에서 사용자 이름 가져오기

    # 내일과 모레 날짜 계산
    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    day_after_tomorrow = today + timedelta(days=2)

    # 날짜를 'YYYY-MM-DD' 형식으로 변환하여 초기값 설정
    default_start_date = tomorrow.strftime('%Y-%m-%d')
    default_end_date = day_after_tomorrow.strftime('%Y-%m-%d')


    if request.method == 'POST':
        # 폼에서 선택한 값들
        car_type = request.form['car_type']
        fuel_type = request.form['fuel_type']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        pickup_time = request.form['pickup_time']
        return_time = request.form['return_time']

        session['start_date'] = start_date
        session['end_date'] = end_date
        session['pickup_time'] = pickup_time
        session['return_time'] = return_time

        #SQL
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT cars.car_id, cars.car_name, cars.model_year, cars.color, car.car_type, car.fuel_type, car.image_url
            FROM cars
            JOIN car ON cars.car_name = car.car_name AND cars.model_year = car.model_year AND cars. color = car.color
            LEFT JOIN maintenance m ON cars.car_id = m.car_id
            WHERE (m.car_id IS NULL OR m.status = '완료')  # 유지보수 테이블에 없거나, 상태가 '완료'인 차량만
        """

        filters = []

        # 조건에 맞는 차량을 쿼리로 필터링
        if car_type:
            query += " AND car_type = %s"
            filters.append(car_type)

        if fuel_type:
            query += " AND fuel_type = %s"
            filters.append(fuel_type)

        # 예약되지 않은 차량만 선택
        if start_date and end_date:
            query += """
                AND NOT EXISTS (
                    SELECT 1
                    FROM reservation r
                    WHERE r.car_id = cars.car_id
                      AND (
                            (r.start_date BETWEEN %s AND %s) OR
                            (r.end_date BETWEEN %s AND %s) OR
                            (r.start_date <= %s AND r.end_date >= %s)
                            )
                        )
                    """
            # 날짜 값을 filters 리스트에 추가합니다.
            filters.extend([start_date, end_date, start_date, end_date, start_date, end_date])  

        
        cursor.execute(query, filters)
        cars = cursor.fetchall()
        cursor.close()

        # 예약 페이지로 다시 렌더링하면서 데이터 전달
        return render_template('reservation.html', 
                               user_logged_in=user_logged_in, 
                               name=name, 
                               cars=cars,
                               car_type=car_type,
                               fuel_type=fuel_type,
                               start_date=start_date,
                               end_date=end_date,
                               pickup_time=pickup_time,
                               return_time=return_time)
    else:
        # GET 방식으로 페이지 열기

        car_type = request.args.get('car_type', '')  # 기본값을 빈 문자열로 설정
        fuel_type = request.args.get('fuel_type', '')  # 기본값을 빈 문자열로 설정
        start_date = session.get('start_date', default_start_date)
        end_date = session.get('end_date', default_end_date)
        pickup_time = session.get('pickup_time', '9:00')
        return_time = session.get('return_time', '9:00')

        session['start_date'] = start_date
        session['end_date'] = end_date
        session['pickup_time'] = pickup_time
        session['return_time'] = return_time
        session['pickup_time'] = pickup_time
        session['return_time'] = return_time

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # filters를 빈 리스트로 초기화
        filters = []

        query = """
            SELECT cars.car_id, cars.car_name, cars.model_year, cars.color, car.car_type, car.fuel_type, car.image_url
            FROM cars
            JOIN car ON cars.car_name = car.car_name AND cars.model_year = car.model_year AND cars. color = car.color
            LEFT JOIN maintenance m ON cars.car_id = m.car_id
            WHERE (m.car_id IS NULL OR m.status = '완료')  # 유지보수 테이블에 없거나, 상태가 '완료'인 차량만
        """

        #예약날짜 이용가능 차량필터링
        query += """
            AND NOT EXISTS (
                SELECT 1
                FROM reservation r
                WHERE r.car_id = cars.car_id
                  AND (
                      (r.start_date BETWEEN %s AND %s) OR
                      (r.end_date BETWEEN %s AND %s) OR
                      (r.start_date <= %s AND r.end_date >= %s)
                  )
            )
        """
        # 날짜 값을 filters 리스트에 추가합니다.
        filters.extend([start_date, end_date, start_date, end_date, start_date, end_date])


        cursor.execute(query, filters)
        cars = cursor.fetchall()
        cursor.close()

        return render_template('reservation.html', 
                               user_logged_in=user_logged_in, 
                               name=name, 
                               cars=cars,
                               car_type=car_type,
                               fuel_type=fuel_type,
                               start_date=start_date,
                               end_date=end_date,
                               default_start_date = default_start_date,
                               default_end_date = default_end_date,
                               pickup_time=pickup_time,
                               return_time=return_time)

#운전자 정보입력 페이지
@app.route('/driver_info', methods=['GET', 'POST'])
def driver_info():
    # 로그인 상태 확인
    user_logged_in = 'user_id' in session
    name = session.get('name', '')

    if request.method == 'POST':
        # 운전자의 정보 받기
        driver_name = request.form['driver_name']
        driver_phone = request.form['driver_phone']

        # 운전자의 정보를 세션에 저장
        session['driver_name'] = driver_name
        session['driver_phone'] = driver_phone

        # 예약 ID와 운전자의 정보를 결제 전 세션에 저장한 후, 결제 페이지로 리다이렉트
        return redirect('/payment')  # 결제 페이지로 리다이렉트
    else:
        return render_template('driver_info.html', user_logged_in=user_logged_in, name=name)




#보유차종 페이지
@app.route('/car')
def car():
    # 로그인 상태 확인
    user_logged_in = 'user_id' in session
    name = session.get('name', '')  # 세션에서 사용자 이름 가져오기

    car_type = request.args.get('car_type')
    fuel_type = request.args.get('fuel_type')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # 기본 쿼리 작성 (차량 목록을 가져오는 쿼리)
    query = """
        SELECT *
        FROM car
        WHERE 1=1  -- 항상 true, 나중에 조건을 추가할 수 있도록
    """
    params = []  # 쿼리의 조건에 추가할 파라미터들을 담을 리스트
    
    # car_type이 주어지면 조건 추가
    if car_type:
        query += " AND car_type = %s"
        params.append(car_type)

    # fuel_type이 주어지면 조건 추가
    if fuel_type:
        query += " AND fuel_type = %s"
        params.append(fuel_type)

    # ORDER BY 추가(최근연식모델부터, 이름순으로)
    query += " ORDER BY model_year DESC, car_name ASC"

    # 쿼리 실행
    cursor.execute(query, params)
    cars = cursor.fetchall()  # 쿼리 실행 결과 가져오기

    # DB 연결 종료
    cursor.close()
    connection.close()
    
    # 템플릿에 차량 정보 전달
    return render_template('car.html', user_logged_in=user_logged_in, name=name, cars=cars, car_type=car_type, fuel_type=fuel_type)



#이용안내 페이지 렌더링
@app.route('/guide')
def guide():
    # 로그인 상태 확인
    user_logged_in = 'user_id' in session
    name = session.get('name', '')  # 세션에서 사용자 이름 가져오기

    return render_template('guide.html', user_logged_in=user_logged_in, name=name)


#고객센터 페이지 렌더링
@app.route('/support')
def support():
    # 로그인 상태 확인
    user_logged_in = 'user_id' in session
    name = session.get('name', '')  # 세션에서 사용자 이름 가져오기

    return render_template('support.html', user_logged_in=user_logged_in, name=name)







# 서버 실행
if __name__ == '__main__':
    app.run(debug=True)

