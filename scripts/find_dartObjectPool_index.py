import idaapi
import idautils
import idc
import ida_search
import ida_kernwin
from loguru import logger
import os
import ida_bytes
import ida_segment

# # get file name and remove ext
# filename = os.path.basename(__file__).replace(".py", "")

# # 設定日誌檔案路徑
# log_filename = os.path.join(idaapi.get_user_idadir(), "logs", f"{filename}.log")
# print(log_filename)
# logger.add(log_filename, format="{time} {level} {message}", level="INFO", rotation="100MB")


def get_member_name_by_index(struct_name, index):
    struct_id = idc.get_struc_id(struct_name)
    if struct_id == idc.BADADDR:
        logger.error(f"结构体 '{struct_name}' 不存在。")
        return None

    offset = 0
    while True:
        member_id = idc.get_member_id(struct_id, offset)
        if member_id == idc.BADADDR:
            break

        member_size = idc.get_member_size(struct_id, offset)
        if offset <= index < offset + member_size:
            return idc.get_member_name(struct_id, offset)

        offset += member_size

    logger.error(f"在结构体 '{struct_name}' 中未找到对应索引 {index} 的成员。")
    return None

def search_with_mask(start_ea, end_ea, pattern, mask):
    ea = 0x12FEA90  #start_ea
    pattern_length = len(pattern)

    total_size = end_ea - start_ea
    last_percentage = -1
    while ea != idaapi.BADADDR and ea < end_ea:
        # Calculate and log progress percentage
        current_progress = ea - start_ea
        current_percentage = int((current_progress / total_size) * 100)
        if current_percentage != last_percentage and current_percentage % 5 == 0:
            #logger.info(f"Search progress: {current_percentage}%")
            last_percentage = current_percentage


        # Read the next chunk of data based on the length of the pattern
        bytes_to_check = ida_bytes.get_bytes(ea, pattern_length)

        if bytes_to_check is None:
            break

        match = True
        for i in range(pattern_length):
            if mask[i] and bytes_to_check[i] != pattern[i]:
                match = False
                break

        if match:
            logger.info(f"Pattern found at address: {hex(ea)} - {hex(ea + 4)}")
            # 添加註解
            #idc.set_cmt(ea + 4, "Pattern matched here", 0)

            # 檢查指令是否使用了 X27 並計算 X? 的結果
            insn_add = idaapi.insn_t()
            insn_ldr = idaapi.insn_t()
            if idaapi.decode_insn(insn_add, ea):
                logger.debug(f"[{current_percentage}%] Decoded ADD instruction at {hex(ea)}: {idc.GetDisasm(ea)}")
            else:
                logger.error(f"[{current_percentage}%] Failed to decode ADD instruction at {hex(ea)}")

            if idaapi.decode_insn(insn_ldr, ea + 4):
                logger.debug(f"[{current_percentage}%] Decoded LDR instruction at {hex(ea + 4)}: {idc.GetDisasm(ea + 4)}")
            else:
                logger.error(f"[{current_percentage}%] Failed to decode LDR instruction at {hex(ea + 4)}")

            if insn_add.itype == idaapi.ARM_add and insn_ldr.itype == idaapi.ARM_ldr:
                logger.debug(f"[{current_percentage}%] ADD instruction type: {insn_add.itype}")
                logger.debug(f"[{current_percentage}%] LDR instruction type: {insn_ldr.itype}")
                # Map register numbers to X registers (assuming ARM64)
                def reg_to_x(reg_num):
                    return f"X{reg_num - 129}" if 129 <= reg_num <= 160 else f"reg{reg_num}"
                
                logger.debug(f"[{current_percentage}%] ADD instruction operands: {reg_to_x(insn_add.ops[0].reg)}({insn_add.ops[0].reg}), "
                           f"{reg_to_x(insn_add.ops[1].reg)}({insn_add.ops[1].reg}), "
                           f"{reg_to_x(insn_add.ops[2].reg)}({insn_add.ops[2].reg})")
                logger.debug(f"[{current_percentage}%] Registers as hex: reg0=0x{insn_add.ops[0].reg:x}, reg1=0x{insn_add.ops[1].reg:x}")
                
                # Adjust comparison for the 129 offset
                if (insn_add.ops[1].reg - 129) == 27:  # X27 is register 156 (129 + 27)
                    logger.debug(f"[{current_percentage}%] Second operand reg: {insn_add.ops[1].reg}")
                    
                    # 取得 immediate value 並進行 LSL#12 移位
                    imm_value = insn_add.ops[2].value
                    shift_amount = 12  # ARM64 的 LSL#12
                    offset = imm_value << shift_amount  # 例如: 0x26 << 12 = 0x26000
                    
                    # 加上 LDR 指令的 offset
                    ldr_offset = insn_ldr.ops[1].addr  # 例如: 0x348
                    
                    # 計算總偏移量
                    total_offset = offset + ldr_offset  # 0x26000 + 0x348 = 0x26348
                    
                    # 判斷 ea + 4 的是否有註解，如果而且包含字串 "[pp+" 和 "DartObjectPool" 則不添加註解
                    comment = idc.get_cmt(ea + 4, 0)
                  
                    # 取得結構體成員名稱
                    struct_name = "DartObjectPool"
                    member_name = get_member_name_by_index(struct_name, total_offset)

                    # 添加註解
                    comment=f"[pp+{hex(total_offset)}] {struct_name}.{member_name}"
                    
                    # 只添加 offset 資訊的註解
                    idc.set_cmt(ea + 4, comment, 0)  
                    
                    logger.info(f"[{current_percentage}%] Found at {hex(ea)}: {comment}")

        # 没有匹配到则继续逐字节查找
        ea += 4

# 遍历所有段并只选择CODE段进行搜索
for seg_start in idautils.Segments():
    seg = idaapi.getseg(seg_start)  # 获取 segment_t 对象
    seg_name = ida_segment.get_segm_name(seg)  # 获取段的名称
    seg_type = seg.type  # 直接获取段类型
    
    # SEG_CODE (0x2) 表示这是一个代码段
    if seg_type == idaapi.SEG_CODE:
        logger.info(f"Searching in segment: {seg_name}")

        # 定义搜索的字节模式和掩码
        # 使用 0x00 表示通配符，其他值表示固定字节
        pattern = bytes([
            0x00, 0x00, 0x40, 0x91,  # 70 2B 40 91 -> ADD X16, X27, #0xA,LSL#12
            0x00, 0x00, 0x00, 0xF9   # 10 1E 41 F9 -> LDR X16, [X16,#0x238]
        ])
        mask = [
            False, False, True, True, 
            False, False, False, True
        ]  # True 表示需要匹配的字節，False 表示通配符

        # 搜索的字节模式和掩码
        # .text:0000000000FCA1FC 61 1F 41 91 -> ADD X1, X27, #0x47,LSL#12 ; 'G'
        # .text:0000000000FCA200 21 2C 47 F9 -> LDR X1, [X1,#0xE58]
                                                                        
        # 调用搜索函数在代码段内进行搜索
        start_ea = seg_start
        end_ea = seg.end_ea  # 使用 seg.end_ea 获取结束地址
        
        search_with_mask(start_ea, end_ea, pattern, mask)