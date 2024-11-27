# 匯出Structs View 的內容
# 使用方法：將此文件放到 IDA Pro 的目錄下，然後在 IDA Pro 的命令行中執行 execfile("export_struct.py") 即可
 
import ida_struct
import ida_idaapi
import ida_typeinf

# 文件保存路径
output_file = "C:/Users/jimmy/Projects/flutter-reverse-note/idapro/structures.h"

def export_structs():
    with open(output_file, "w", encoding="utf-8", errors="ignore") as f:  # 使用 utf-8 编码，并忽略错误
        # 获取所有结构的数量
        for idx in range(ida_struct.get_struc_qty()):
            struct_id = ida_struct.get_struc_by_idx(idx)
            struct = ida_struct.get_struc(struct_id)
            if struct:
                struct_name = ida_struct.get_struc_name(struct_id)
                f.write(f"// Structure: {struct_name}\n")
                f.write(f"struct {struct_name} {{\n")
                
                # 遍历结构的所有成员，使用 index 作为成员的索引
                index = 0
                member_offset = ida_struct.get_struc_first_offset(struct)
                while member_offset != ida_idaapi.BADADDR:
                    member = ida_struct.get_member(struct, member_offset)
                    if member:
                        member_name = ida_struct.get_member_name(member.id) or f"unnamed_{member.id}"
                        member_size = ida_struct.get_member_size(member)
                        
                        # 使用 ida_typeinf 获取类型信息
                        tif = ida_typeinf.tinfo_t()
                        if ida_struct.get_member_tinfo(tif, member):
                            member_type = tif.dstr()  # 获取类型描述字符串
                        else:
                            member_type = "unknown_type"
                        
                        # 获取行注释和重复注释
                        try:
                            comment = ida_struct.get_member_cmt(member.id, False) or ida_struct.get_member_cmt(member.id, True) or "No Comment"
                        except UnicodeDecodeError:
                            comment = "Invalid Unicode in Comment"

                        f.write(f"    // Index: {index}, Offset: {hex(member_offset)}, Comment: {comment}\n")
                        f.write(f"    {member_type} {member_name}; // Size: {member_size}\n")

                    member_offset = ida_struct.get_struc_next_offset(struct, member_offset)
                    index += 1  # 增加索引

                f.write("};\n\n")

export_structs()