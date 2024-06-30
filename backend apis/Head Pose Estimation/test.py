import cv2
import mediapipe as mp
import numpy as np

def initialize_face_mesh():
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    return face_mesh, mp_face_mesh

def get_drawing_spec():
    mp_drawing = mp.solutions.drawing_utils
    drawing_spec = mp_drawing.DrawingSpec(thickness=1, circle_radius=1)
    return drawing_spec, mp_drawing

def process_frame(face_mesh, img):
    img_rgb = cv2.cvtColor(cv2.flip(img, 1), cv2.COLOR_BGR2RGB)
    res = face_mesh.process(img_rgb)
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    return res, img_bgr

def calculate_head_pose(res, h, w):
    three_mat = []
    two_mat = []
    key_landmarks = [33, 263, 1, 61, 291, 199, 474, 475, 476, 477, 473, 469, 470, 471, 472]

    if res.multi_face_landmarks:
        for face_landmarks in res.multi_face_landmarks:
            for idx, land_marks in enumerate(face_landmarks.landmark):
                if idx in key_landmarks:
                    x, y = int(land_marks.x * w), int(land_marks.y * h)
                    z = land_marks.z
                    two_mat.append([x, y])
                    three_mat.append([x, y, z])

            two_mat = np.array(two_mat, dtype=np.float64)
            three_mat = np.array(three_mat, dtype=np.float64)

            focal_length = 1 * w
            cam_mat = np.array([[focal_length, 0, w / 2],
                                [0, focal_length, h / 2],
                                [0, 0, 1]])

            distort = np.zeros((4, 1), dtype=np.float64)
            success, rot_vec, trans_vec = cv2.solvePnP(three_mat, two_mat, cam_mat, distort)

            if success:
                rmat, _ = cv2.Rodrigues(rot_vec)
                angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
                x_angle = angles[0] * 360
                y_angle = angles[1] * 360
                z_angle = angles[2] * 360
                return x_angle, y_angle, z_angle, face_landmarks
    return None, None, None, None

def determine_head_position(x_angle, y_angle):
    if y_angle < -11:
        return "Left"
    elif y_angle > 11:
        return "Right"
    elif x_angle < -15:
        return "Down"
    elif x_angle > 13:
        return "Up"
    else:
        return "Forward"

def distraction(x_angle, y_angle):
    if determine_head_position(x_angle, y_angle) == "Forward":
        return "No Distraction"
    else:
        return "Distraction"

def draw_annotations(img_bgr, x_angle, y_angle, z_angle, text, face_landmarks, drawing_spec, mp_drawing, mp_face_mesh):
    cv2.putText(img_bgr, text, (20, 50), cv2.FONT_HERSHEY_COMPLEX, 2, (0, 255, 0), 2)
    mp_drawing.draw_landmarks(image=img_bgr, landmark_list=face_landmarks,
                              connections=mp_face_mesh.FACEMESH_TESSELATION,
                              landmark_drawing_spec=drawing_spec,
                              connection_drawing_spec=drawing_spec)

def draw_iris_landmarks(img_bgr, face_landmarks, mp_drawing, drawing_spec):
    iris_landmarks_left = [474, 475, 476, 477]  # Left eye
    iris_landmarks_right = [469, 470, 471, 472]  # Right eye

    for idx in iris_landmarks_left + iris_landmarks_right:
        if idx < len(face_landmarks.landmark):
            landmark = face_landmarks.landmark[idx]
            x, y = int(landmark.x * img_bgr.shape[1]), int(landmark.y * img_bgr.shape[0])
            cv2.circle(img_bgr, (x, y), 2, (0, 255, 0), -1)

    return iris_landmarks_left, iris_landmarks_right

def get_eye_region(img, face_landmarks, eye_landmarks):
    h, w, _ = img.shape
    x_min = w
    y_min = h
    x_max = 0
    y_max = 0

    for idx in eye_landmarks:
        if idx < len(face_landmarks.landmark):
            landmark = face_landmarks.landmark[idx]
            x, y = int(landmark.x * w), int(landmark.y * h)
            if x < x_min:
                x_min = x
            if y < y_min:
                y_min = y
            if x > x_max:
                x_max = x
            if y > y_max:
                y_max = y

    margin = 5  # Add some margin around the eye region
    x_min = max(0, x_min - margin)
    y_min = max(0, y_min - margin)
    x_max = min(w, x_max + margin)
    y_max = min(h, y_max + margin)

    if x_max > x_min and y_max > y_min:
        return img[y_min:y_max, x_min:x_max]
    else:
        return None

def main():
    face_mesh, mp_face_mesh = initialize_face_mesh()
    drawing_spec, mp_drawing = get_drawing_spec()

    cam = cv2.VideoCapture(0)
    while cam.isOpened():
        flag, img = cam.read()
        if not flag:
            break

        h, w, _ = img.shape
        res, img_bgr = process_frame(face_mesh, img)
        x_angle, y_angle, z_angle, face_landmarks = calculate_head_pose(res, h, w)

        if x_angle is not None and y_angle is not None and z_angle is not None:
            text = distraction(x_angle, y_angle)
            draw_annotations(img_bgr, x_angle, y_angle, z_angle, text, face_landmarks, drawing_spec, mp_drawing, mp_face_mesh)
            iris_landmarks_left, iris_landmarks_right = draw_iris_landmarks(img_bgr, face_landmarks, mp_drawing, drawing_spec)

            left_eye_img = get_eye_region(img_bgr, face_landmarks, iris_landmarks_left)
            right_eye_img = get_eye_region(img_bgr, face_landmarks, iris_landmarks_right)

            if left_eye_img is not None:
                cv2.imshow('Left Eye', left_eye_img)
            if right_eye_img is not None:
                cv2.imshow('Right Eye', right_eye_img)

        cv2.imshow('MediaPipe Face Mesh', img_bgr)

        if cv2.waitKey(5) & 0xFF == 27:
            break

    cam.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
