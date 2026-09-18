import plotly.io as pio
import plotly.graph_objects as go

def setup_editorial_theme():
    """
    Thiết lập template Plotly theo chuẩn thiết kế Editorial UI (Báo chí học thuật).
    Tự động áp dụng nền off-white báo giấy, font Serif cho tiêu đề và Sans-serif cho trục dữ liệu,
    đồng thời cấu hình các đường lưới mảnh tối giản.
    """
    editorial_layout = go.Layout(
        # Nền giấy báo ngà sáng đặc trưng NYT
        paper_bgcolor='#FAF8F5',
        plot_bgcolor='rgba(0,0,0,0)',
        
        # Typography Sans-serif cho nội dung và số liệu
        font=dict(
            family="Plus Jakarta Sans, sans-serif",
            size=12,
            color="#1C1C1C"
        ),
        
        # Đường Baseline mỏng, ẩn viền bao (spines) phía trên và phải
        xaxis=dict(
            gridcolor="#EBE9E4",
            linecolor="#1C1C1C",
            tickfont=dict(color="#1C1C1C"),
            showline=True,
            mirror=False
        ),
        yaxis=dict(
            gridcolor="#EBE9E4",
            linecolor="#1C1C1C",
            tickfont=dict(color="#1C1C1C"),
            showline=True,
            mirror=False
        ),
        
        # Tiêu đề biểu đồ dùng font Serif Georgia/Lora cổ điển
        title=dict(
            font=dict(
                family="Lora, Georgia, serif",
                size=16,
                color="#1C1C1C"
            )
        )
    )
    
    # Tạo Template đối tượng từ cấu hình layout
    editorial_template = pio.templates.create(
        layout=editorial_layout
    )
    
    # Đăng ký template mới và thiết lập làm mặc định
    pio.templates['editorial'] = editorial_template
    pio.templates.default = 'editorial'

# Tự động thực thi khi module được import
setup_editorial_theme()
