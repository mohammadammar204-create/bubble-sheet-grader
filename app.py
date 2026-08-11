def scan_bubbles_from_image(image_bytes, num_questions=10):
    np_img = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

    if image is None:
        return None, None, "Invalid image format uploaded."

    # 1. Attempt QR decoding
    qr_meta = decode_sheet_qr(image)

    h_img, w_img = image.shape[:2]

    # 2. Convert to grayscale and apply inverse thresholding
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )[1]

    # 3. Find contours
    contours, _ = cv2.findContours(
        thresh.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )
    bubble_contours = []

    # Filter out corner squares & non-bubble shapes dynamically relative to page width
    min_dim = int(w_img * 0.015)  # Dynamic scale filter
    max_dim = int(w_img * 0.08)

    for c in contours:
        (x, y, w, h) = cv2.boundingRect(c)
        ar = w / float(h)

        # Ignore corner alignment squares (which sit at edges)
        is_corner = (
            (x < w_img * 0.1 and y < h_img * 0.1)
            or (x > w_img * 0.85 and y < h_img * 0.1)
            or (x < w_img * 0.1 and y > h_img * 0.85)
            or (x > w_img * 0.85 and y > h_img * 0.85)
        )

        if (
            not is_corner
            and min_dim <= w <= max_dim
            and min_dim <= h <= max_dim
            and 0.70 <= ar <= 1.30
        ):
            bubble_contours.append(c)

    if not bubble_contours:
        return (
            None,
            qr_meta,
            "No bubbles detected. Check image contrast or alignment.",
        )

    # Sort bubbles top-to-bottom
    bubble_contours = sorted(
        bubble_contours, key=lambda c: cv2.boundingRect(c)[1]
    )

    # Group bubbles into horizontal rows
    rows = []
    current_row = []
    prev_y = None
    y_threshold = int(h_img * 0.018)  # Scaled threshold based on image height

    for cnt in bubble_contours:
        _, y, _, _ = cv2.boundingRect(cnt)
        if prev_y is None or abs(y - prev_y) <= y_threshold:
            current_row.append(cnt)
        else:
            rows.append(current_row)
            current_row = [cnt]
        prev_y = y

    if current_row:
        rows.append(current_row)

    options = ["A", "B", "C", "D"]
    answers = {}

    for q_idx in range(1, num_questions + 1):
        if q_idx - 1 >= len(rows):
            break

        # Sort left-to-right for options A, B, C, D
        row_contours = sorted(
            rows[q_idx - 1], key=lambda c: cv2.boundingRect(c)[0]
        )

        # Skip question numbers or misidentified text contours on left side
        if len(row_contours) > 4:
            row_contours = row_contours[-4:]

        marked_idx = None
        max_pixels = 0

        for opt_idx, cnt in enumerate(row_contours[:4]):
            mask = np.zeros(thresh.shape, dtype="uint8")
            cv2.drawContours(mask, [cnt], -1, 255, -1)
            mask = cv2.bitwise_and(thresh, thresh, mask=mask)
            total_pixels = cv2.countNonZero(mask)

            # Detect filled bubbles relative to contour size
            if total_pixels > max_pixels and total_pixels > int(
                min_dim * min_dim * 0.8
            ):
                max_pixels = total_pixels
                marked_idx = opt_idx

        answers[str(q_idx)] = (
            options[marked_idx]
            if (marked_idx is not None and marked_idx < 4)
            else "None"
        )

    return answers, qr_meta, None
