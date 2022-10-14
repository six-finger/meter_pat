import math

def central_pos(arr):
    # 获得bbox中心坐标
    return (arr[0] + arr[2]) / 2, (arr[1] + arr[3]) / 2


def angle_pos_lst(arr):
    # 获得bbox四个角的坐标
    return [(arr[0], arr[1]), (arr[2], arr[1]), (arr[2], arr[3]), (arr[0], arr[3])]


def dot(a, b):
    # 求点积
    return sum(list(map(lambda e, f: e * f, a, b)))


def dist(a, b):
    # 求距离
    return pow(pow(a[0] - b[0], 2) + pow(a[1] - b[1], 2), 0.5)


def get_ptr_tip(ctr_arr, ptr_arr):
    ctr = central_pos(ctr_arr)
    angle_lst = angle_pos_lst(ptr_arr)
    dist_lst = []
    for v in angle_lst:
        dist_lst.append(dist(v, ctr))
    return angle_lst[dist_lst.index(max(dist_lst))]  # (a, b)


def read_num(num_arr):
    scale_dict = dict(zip([5, 6, 7, 9], [1.6, 50, 120, 160]))
    num_cnt = len(num_arr)
    max_scale = scale_dict.get(num_cnt)
    if max_scale is None:
        max_scale = -1
    return num_cnt, max_scale  # 5, 1.6


def degree_angle(ctr, a, b):
    # 求由c,a,b三个点构成的角c的度数
    ca = list(map(lambda e, f: e - f, a, ctr))
    cb = list(map(lambda e, f: e - f, b, ctr))
    len_ca = pow(pow(ca[0], 2) + pow(ca[1], 2), 0.5)
    len_cb = pow(pow(cb[0], 2) + pow(cb[1], 2), 0.5)
    return math.acos(dot(ca, cb) / (len_ca * len_cb))


def vector_angle(ctr, a):
    assert ctr[1] > 0, "Error:: the y-axis of ctr should larger than 0."
    b = (ctr[0], 9999999999999)  # 向量cb指向y-axis负方向.
    angle = degree_angle(ctr, a, b)
    if a[0] > ctr[0]:  # 角bca 大于 pi.
        angle = 2 * math.pi - angle
    return angle


def sort_nums(num_lst, ctr, method):
    # 刻度数排序
    left = [v for v in num_lst if v[0] < ctr[0]]
    right = [v for v in num_lst if v[0] >= ctr[0]]
    left.sort(key=lambda v: v[1], reverse=True)
    right.sort(key=lambda v: v[1], reverse=False)
    num_lst = left + right
    num_lst2 = num_lst
    if method == 'Base':
        return num_lst
    if method == 'ByAngle':
        # 相邻两个刻度数与表心的夹角最大
        neighbor_num_angle_lst = [degree_angle(ctr, num_lst2[-1], num_lst2[0])]
        neighbor_num_angle_lst.extend([degree_angle(ctr, num_lst2[i], num_lst2[i + 1]) for i in range(len(num_lst2) - 1)])
        k = neighbor_num_angle_lst.index(max(neighbor_num_angle_lst))
        while k != 0:
            num_lst2.append(num_lst2[0])
            num_lst2.pop(0)
            k -= 1
        return num_lst2


def cal_indication(meter_elements, meter_int):

    ctr_arr, ptr_arr, num_arr = meter_elements[0], meter_elements[1], meter_elements[2]
    if len(num_arr) <= 1:
        return -1
    # 获取指针尖端坐标 ptr_tip，刻度中心坐标列表 num_lst， 表心中心坐标 ctr
    ptr_tip = get_ptr_tip(ctr_arr, ptr_arr)
    num_lst = [central_pos(v) for v in num_arr]    # 正向排序 num_lst
    ctr = central_pos(ctr_arr)

    # 刻度数排序（0不一定在首位）
    if meter_int == 0:      # 假设Press是已被矫正的图像，左下角为0刻度数
        num_lst = sort_nums(num_lst, ctr, 'Base')
    else:
        num_lst = sort_nums(num_lst, ctr, 'ByAngle')

    # 计算夹角
    angle_lst = []
    for i, v in enumerate(num_lst):
        angle_lst.append(vector_angle(ctr, v))
    ptr_angle = vector_angle(ctr, ptr_tip)

    # 找到指针左侧刻度数的位置下标pos
    # 假设Press是已被矫正的图像，左下角为0刻度数
    if meter_int == 0:
        pos = 0
    else:
        pos = -1
        min_index = angle_lst.index(min(angle_lst))
        max_index = angle_lst.index(max(angle_lst))
        if (ptr_angle <= angle_lst[min_index] and ptr_angle <= angle_lst[max_index]) \
                or (ptr_angle >= angle_lst[min_index] and ptr_angle >= angle_lst[max_index]):
            pos = max_index
        for i in range(len(angle_lst) - 1):
            if angle_lst[i] < ptr_angle < angle_lst[i + 1]:
                pos = i
                break

    # 通过入参classes_int判断最大量程（[0,1,2,3] 对应[1.6, 50, 160, 120] 对应间隔数[4, 5, 8, 6]）
    scale_cfg, sep_cfg = [1.6, 50, 160, 120], [5, 6, 9, 7]
    max_scale = scale_cfg[meter_int]
    num_cnt = sep_cfg[meter_int]
    real = (pos + ((ptr_angle - angle_lst[pos]) % (2 * math.pi)) /
                  ((angle_lst[(pos + 1) % len(angle_lst)] - angle_lst[pos]) % (2 * math.pi))) \
                 * max_scale / (num_cnt - 1)
    # print('{}=({} + ({} - {})/({} - {}) * {} / {}'
    #       .format(real, pos, ptr_angle, angle_lst[pos], angle_lst[(pos + 1) % len(angle_lst)], angle_lst[pos],
    #               max_scale, (num_cnt - 1)))
    est_lst = [f'{real:.2f}', f'{real:.1f}', f'{real:.1f}', f'{real:.1f}']
    estimate = est_lst[meter_int]
    return estimate


def split_predict_arr(bboxes, labels, thres):
    """
    return:
        ctr_arr: 1 pair of central coordinates;
        ptr_arr: 4 pairs of coordinates(needing determining in function calculate_indication()), in which:
                0-> top-left, 1-> top-right, 2-> bottom-right, 3-> bottom-left
        num_arr: n pairs of central coordinates.
    """
    ctr_arr = bboxes[labels == 0][0][0:4]
    ptr_arr = bboxes[labels == 1][0][0:4]
    num_arr = []
    for i, v in enumerate(bboxes[labels == 2]):
        if v[4] < thres:
            continue
        num_arr.append([cont for j, cont in enumerate(v) if j < 4])
    return ctr_arr, ptr_arr, num_arr

