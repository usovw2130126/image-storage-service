from PIL import Image, ImageOps
import io
from typing import Dict, Optional, Tuple
from app.config import DEFAULT_QUALITY, DEFAULT_RESIZE_MODE
from app.utils.security import ImageServiceError

class ImageProcessor:
    """圖片處理服務"""
    
    @staticmethod
    def get_image_info(file_content: bytes) -> Dict[str, any]:
        """獲取圖片資訊"""
        try:
            with Image.open(io.BytesIO(file_content)) as img:
                return {
                    "format": img.format,
                    "dimensions": {"width": img.width, "height": img.height},
                    "mode": img.mode
                }
        except Exception as e:
            raise ImageServiceError(
                code="IMAGE_PROCESSING_ERROR",
                message="Failed to process image",
                status_code=400,
                details=f"Cannot read image: {str(e)}"
            )
    
    @staticmethod
    def resize_image(file_content: bytes, width: Optional[int] = None, 
                    height: Optional[int] = None, quality: int = DEFAULT_QUALITY,
                    output_format: Optional[str] = None, 
                    mode: str = DEFAULT_RESIZE_MODE) -> Tuple[bytes, str]:
        """調整圖片大小"""
        try:
            with Image.open(io.BytesIO(file_content)) as img:
                original_format = img.format.lower() if img.format else 'jpeg'
                target_format = output_format.lower() if output_format else original_format
                
                # 確保 RGB 模式（避免調色盤模式的問題）
                if img.mode in ('RGBA', 'LA'):
                    # 保持透明度
                    if target_format in ['jpg', 'jpeg']:
                        # JPEG 不支援透明度，轉換為白色背景
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'RGBA':
                            background.paste(img, mask=img.split()[-1])
                        img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 如果沒有指定尺寸，返回原圖
                if width is None and height is None:
                    output_buffer = io.BytesIO()
                    save_format = 'JPEG' if target_format in ['jpg', 'jpeg'] else target_format.upper()
                    
                    save_kwargs = {'format': save_format}
                    if save_format == 'JPEG':
                        save_kwargs['quality'] = quality
                        save_kwargs['optimize'] = True
                    
                    img.save(output_buffer, **save_kwargs)
                    return output_buffer.getvalue(), target_format
                
                # 計算目標尺寸
                original_width, original_height = img.size
                
                if width and height:
                    target_size = (width, height)
                elif width:
                    # 按寬度等比縮放
                    ratio = width / original_width
                    target_size = (width, int(original_height * ratio))
                else:
                    # 按高度等比縮放
                    ratio = height / original_height
                    target_size = (int(original_width * ratio), height)
                
                # 根據模式調整圖片
                if mode == 'fit':
                    # 保持比例，完整顯示圖片
                    img.thumbnail(target_size, Image.Resampling.LANCZOS)
                elif mode == 'fill':
                    # 填滿目標尺寸，可能會拉伸
                    img = img.resize(target_size, Image.Resampling.LANCZOS)
                elif mode == 'crop':
                    # 裁切並填滿目標尺寸
                    img = ImageOps.fit(img, target_size, Image.Resampling.LANCZOS)
                else:
                    # 預設使用 fit 模式
                    img.thumbnail(target_size, Image.Resampling.LANCZOS)
                
                # 保存到緩衝區
                output_buffer = io.BytesIO()
                save_format = 'JPEG' if target_format in ['jpg', 'jpeg'] else target_format.upper()
                
                save_kwargs = {'format': save_format}
                if save_format == 'JPEG':
                    save_kwargs['quality'] = quality
                    save_kwargs['optimize'] = True
                elif save_format == 'PNG':
                    save_kwargs['optimize'] = True
                elif save_format == 'WEBP':
                    save_kwargs['quality'] = quality
                    save_kwargs['method'] = 6  # 高品質壓縮
                
                img.save(output_buffer, **save_kwargs)
                return output_buffer.getvalue(), target_format
                
        except Exception as e:
            raise ImageServiceError(
                code="IMAGE_PROCESSING_ERROR",
                message="Failed to resize image",
                status_code=500,
                details=str(e)
            )
    
    @staticmethod
    def validate_and_convert_format(format_str: Optional[str]) -> Optional[str]:
        """驗證並轉換圖片格式"""
        if not format_str:
            return None
        
        format_mapping = {
            'jpg': 'jpeg',
            'jpeg': 'jpeg', 
            'png': 'png',
            'webp': 'webp',
            'gif': 'gif'
        }
        
        format_lower = format_str.lower()
        if format_lower not in format_mapping:
            raise ImageServiceError(
                code="INVALID_FORMAT",
                message="Invalid output format",
                status_code=400,
                details=f"Supported formats: {', '.join(format_mapping.keys())}"
            )
        
        return format_mapping[format_lower]