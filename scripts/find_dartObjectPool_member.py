import idaapi
import idc

def get_member_name_by_index(struct_name, index):
    # 獲取結構體 ID
    struct_id = idc.get_struc_id(struct_name)
    if struct_id == idc.BADADDR:
        print(f"結構體 '{struct_name}' 不存在。")
        return None

    # 獲取結構體大小
    struct_size = idc.get_struc_size(struct_id)
    if index < 0 or index >= struct_size:
        print(f"索引 {index} 超出結構體 '{struct_name}' 的範圍（大小為 {struct_size}）。")
        return None

    # 遍歷結構體成員
    offset = 0
    while offset < struct_size:
        # 獲取成員 ID
        member_id = idc.get_member_id(struct_id, offset)
        if member_id == idc.BADADDR:
            offset += 1
            continue

        # 獲取成員大小
        member_size = idc.get_member_size(struct_id, offset)

        # 檢查索引是否在當前成員範圍內
        if offset <= index < offset + member_size:
            # 獲取成員名稱
            member_name = idc.get_member_name(struct_id, offset)
            return member_name

        offset += member_size

    print(f"在結構體 '{struct_name}' 中未找到對應索引 {index} 的成員。")
    return None

# 使用範例
struct_name = "DartObjectPool"
index = 0xD9C8  # 替換為您的索引值
member_name = get_member_name_by_index(struct_name, index)
if member_name:
    print(f"結構體 '{struct_name}' 中索引 {index} 對應的成員名稱為: {member_name}")
