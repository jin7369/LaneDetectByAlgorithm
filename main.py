import cv2
import numpy as np
import math
def lane_detect(image):
    WIDTH, HEIGHT = 640, 480  # 카메라 이미지 가로x세로 크기
    ROI_START_ROW = 300  # 차선을 찾을 ROI 영역의 시작 Row값
    ROI_END_ROW = 380  # 차선을 찾을 ROT 영역의 끝 Row값
    ROI_HEIGHT = ROI_END_ROW - ROI_START_ROW  # ROI 영역의 세로 크기
    L_ROW = 40  # 차선의 위치를 찾기 위한 ROI 안에서의 기준 Row값
    Blue = (255, 0, 0)  # 파란색
    Red = (0, 0, 255)  # 빨간색
    Yellow = (0, 255, 255)  # 노란색

    prev_x_left = 0
    prev_x_right = WIDTH

    img = image.copy()  # 이미지처리를 위한 카메라 원본이미지 저장
    display_img = np.zeros_like(img)  # 디버깅을 위한 디스플레이용 이미지 저장

    # img(원본이미지)의 특정영역(ROI Area)을 잘라내기
    roi_img = img[ROI_START_ROW:ROI_END_ROW, 0:WIDTH]

    # =========================================
    # 원본 칼라이미지를 그레이 회색톤 이미지로 변환하고 
    # 블러링 처리를 통해 노이즈를 제거한 후에 (약간 뿌옇게, 부드럽게)
    # Canny 변환을 통해 외곽선 이미지로 만들기
    # =========================================
    gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
    blur_gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edge_img = cv2.Canny(np.uint8(blur_gray), 60, 75)


    # 잘라낸 이미지에서 HoughLinesP 함수를 사용하여 선분들을 찾음
    all_lines = cv2.HoughLinesP(edge_img, 1, math.pi / 180, 50, 50, 20)

    if all_lines is None:
        cv2.imshow("Lanes positions", display_img)
        cv2.waitKey(1)
        return False, 0, 0

    # =========================================
    # 선분들의 기울기 값을 각각 모두 구한 후에 리스트에 담음. 
    # 기울기의 절대값이 너무 작은 경우 (수평선에 가까운 경우)
    # 해당 선분을 빼고 담음. 
    # =========================================
    slopes = []
    filtered_lines = []

    for line in all_lines:
        x1, y1, x2, y2 = line[0]

        if (x2 == x1):
            slope = 1000.0
        else:
            slope = float(y2 - y1) / float(x2 - x1)

        if 0.2 < abs(slope):
            slopes.append(slope)
            filtered_lines.append(line[0])

    if len(filtered_lines) == 0:
        cv2.imshow("Lanes positions", display_img)
        cv2.waitKey(1)
        return False, 0, 0

    # =========================================
    # 왼쪽 차선에 해당하는 선분과 오른쪽 차선에 해당하는 선분을 구분하여 
    # 각각 별도의 리스트에 담음.
    # =========================================
    left_lines = []
    right_lines = []

    for j in range(len(slopes)):
        Line = filtered_lines[j]
        slope = slopes[j]

        x1, y1, x2, y2 = Line

        # 기울기 값이 음수이고 화면의 왼쪽에 있으면 왼쪽 차선으로 분류함
        # 기준이 되는 X좌표값 = (화면중심값 - Margin값)
        Margin = 0

        if (slope < 0) and (x2 < WIDTH / 2 - Margin):
            left_lines.append(Line.tolist())

        # 기울기 값이 양수이고 화면의 오른쪽에 있으면 오른쪽 차선으로 분류함
        # 기준이 되는 X좌표값 = (화면중심값 + Margin값)
        elif (slope > 0) and (x1 > WIDTH / 2 + Margin):
            right_lines.append(Line.tolist())

    # 디버깅을 위해 차선과 관련된 직선과 선분을 그리기 위한 도화지 준비
    line_draw_img = np.zeros_like(roi_img)

    # 왼쪽 차선에 해당하는 선분은 빨간색으로 표시
    for line in left_lines:
        x1, y1, x2, y2 = line
        cv2.line(line_draw_img, (x1, y1), (x2, y2), Red, 2)

    # 오른쪽 차선에 해당하는 선분은 노란색으로 표시
    for line in right_lines:
        x1, y1, x2, y2 = line
        cv2.line(line_draw_img, (x1, y1), (x2, y2), Yellow, 2)

    # =========================================
    # 왼쪽/오른쪽 차선에 해당하는 선분들의 데이터를 적절히 처리해서 
    # 왼쪽차선의 대표직선과 오른쪽차선의 대표직선을 각각 구함.
    # 기울기와 Y절편값으로 표현되는 아래와 같은 직선의 방적식을 사용함.
    # (직선의 방정식) y = mx + b (m은 기울기, b는 Y절편)
    # =========================================

    # 왼쪽 차선을 표시하는 대표직선을 구함        
    m_left, b_left = 0.0, 0.0
    x_sum, y_sum, m_sum = 0.0, 0.0, 0.0

    # 왼쪽 차선을 표시하는 선분들의 기울기와 양끝점들의 평균값을 찾아 대표직선을 구함
    size = len(left_lines)
    if size != 0:
        for line in left_lines:
            x1, y1, x2, y2 = line
            x_sum += x1 + x2
            y_sum += y1 + y2
            if (x2 != x1):
                m_sum += float(y2 - y1) / float(x2 - x1)
            else:
                m_sum += 0

        x_avg = x_sum / (size * 2)
        y_avg = y_sum / (size * 2)
        m_left = m_sum / size
        b_left = y_avg - m_left * x_avg

        if m_left != 0.0:
            # =========================================
            # (직선 #1) y = mx + b 
            # (직선 #2) y = 0
            # 위 두 직선의 교점의 좌표값 (x1, 0)을 구함.           
            x1 = int((0.0 - b_left) / m_left)

            # =========================================
            # (직선 #1) y = mx + b 
            # (직선 #2) y = ROI_HEIGHT
            # 위 두 직선의 교점의 좌표값 (x2, ROI_HEIGHT)을 구함.               
            x2 = int((ROI_HEIGHT - b_left) / m_left)

            # 두 교점, (x1,0)과 (x2, ROI_HEIGHT)를 잇는 선을 그림
            cv2.line(line_draw_img, (x1, 0), (x2, ROI_HEIGHT), Blue, 2)

    # 오른쪽 차선을 표시하는 대표직선을 구함      
    m_right, b_right = 0.0, 0.0
    x_sum, y_sum, m_sum = 0.0, 0.0, 0.0

    # 오른쪽 차선을 표시하는 선분들의 기울기와 양끝점들의 평균값을 찾아 대표직선을 구함
    size = len(right_lines)
    if size != 0:
        for line in right_lines:
            x1, y1, x2, y2 = line
            x_sum += x1 + x2
            y_sum += y1 + y2
            if (x2 != x1):
                m_sum += float(y2 - y1) / float(x2 - x1)
            else:
                m_sum += 0

        x_avg = x_sum / (size * 2)
        y_avg = y_sum / (size * 2)
        m_right = m_sum / size
        b_right = y_avg - m_right * x_avg

        if m_right != 0.0:
            # =========================================
            # (직선 #1) y = mx + b 
            # (직선 #2) y = 0
            # 위 두 직선의 교점의 좌표값 (x1, 0)을 구함.           
            x1 = int((0.0 - b_right) / m_right)

            # =========================================
            # (직선 #1) y = mx + b 
            # (직선 #2) y = ROI_HEIGHT
            # 위 두 직선의 교점의 좌표값 (x2, ROI_HEIGHT)을 구함.               
            x2 = int((ROI_HEIGHT - b_right) / m_right)

            # 두 교점, (x1,0)과 (x2, ROI_HEIGHT)를 잇는 선을 그림
            cv2.line(line_draw_img, (x1, 0), (x2, ROI_HEIGHT), Blue, 2)

    # =========================================
    # 차선의 위치를 찾기 위한 기준선(수평선)은 아래와 같음.
    #   (직선의 방정식) y = L_ROW 
    # 위에서 구한 2개의 대표직선, 
    #   (직선의 방정식) y = (m_left)x + (b_left)
    #   (직선의 방정식) y = (m_right)x + (b_right)
    # 기준선(수평선)과 대표직선과의 교점인 x_left와 x_right를 찾음.
    # =========================================

    # =========================================
    # 대표직선의 기울기 값이 0.0이라는 것은 직선을 찾지 못했다는 의미임
    # 이 경우에는 교점 좌표값을 기존 저장해 놨던 값으로 세팅함 
    # =========================================
    if m_left == 0.0:
        x_left = prev_x_left  # 변수에 저장해 놓았던 이전 값을 가져옴

    # =========================================
    # 아래 2개 직선의 교점을 구함
    # (직선의 방정식) y = L_ROW  
    # (직선의 방정식) y = (m_left)x + (b_left)
    # =========================================
    else:
        x_left = int((L_ROW - b_left) / m_left)

    # =========================================
    # 대표직선의 기울기 값이 0.0이라는 것은 직선을 찾지 못했다는 의미임
    # 이 경우에는 교점 좌표값을 기존 저장해 놨던 값으로 세팅함 
    # =========================================
    if m_right == 0.0:
        x_right = prev_x_right  # 변수에 저장해 놓았던 이전 값을 가져옴	

    # =========================================
    # 아래 2개 직선의 교점을 구함
    # (직선의 방정식) y = L_ROW  
    # (직선의 방정식) y = (m_right)x + (b_right)
    # =========================================
    else:
        x_right = int((L_ROW - b_right) / m_right)

    # =========================================
    # 대표직선의 기울기 값이 0.0이라는 것은 직선을 찾지 못했다는 의미임
    # 이 경우에 반대쪽 차선의 위치 정보를 이용해서 내 위치값을 정함 
    # =========================================
    if m_left == 0.0 and m_right != 0.0:
        x_left = x_right - 380

    if m_left != 0.0 and m_right == 0.0:
        x_right = x_left + 380

    # 위 이미지를 디버깅용 display_img에 overwrite해서 화면에 디스플레이 함
    display_img[ROI_START_ROW:ROI_END_ROW, 0:WIDTH] = line_draw_img
    return display_img

if __name__ == '__main__':
    img = cv2.imread('img.png')
    img = cv2.resize(img, (640, 480))
    lane_img = lane_detect(img)
    cv2.imshow('lane detected img',lane_img)
    cv2.waitKey(0)