smpte_h264_640x480_yuv420p_bt709_limited.mkv
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=640x480 -vf noise=alls=10:allf=t -c:v libx264 -pix_fmt yuv420p -x264-params colorspace=bt709:colorprim=bt709:transfer=bt709 -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range limited /home/adg/github/video-patterns/smpte_h264_640x480_yuv420p_bt709_limited.mkv -y
frame=   50 fps=0.0 q=-1.0 Lsize=     907KiB time=00:00:01.92 bitrate=3870.6kbits/s speed=2.02x elapsed=0:00:00.95

smpte_h265_640x480_yuv420p_bt709_limited.mkv
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=640x480 -vf noise=alls=10:allf=t -c:v libx265 -pix_fmt yuv420p -x265-params colorprim=bt709:transfer=bt709:colormatrix=bt709 -color_range limited /home/adg/github/video-patterns/smpte_h265_640x480_yuv420p_bt709_limited.mkv -y
frame=   50 fps=0.0 q=35.1 Lsize=      23KiB time=00:00:01.92 bitrate=  97.5kbits/s speed=3.73x elapsed=0:00:00.51

smpte_h265_640x480_yuv422p10le_bt709_limited.mkv
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=640x480 -vf noise=alls=10:allf=t -c:v libx265 -pix_fmt yuv422p10le -x265-params colorprim=bt709:transfer=bt709:colormatrix=bt709 -color_range limited /home/adg/github/video-patterns/smpte_h265_640x480_yuv422p10le_bt709_limited.mkv -y
frame=   50 fps= 47 q=35.8 Lsize=      24KiB time=00:00:01.92 bitrate= 103.4kbits/s speed= 1.8x elapsed=0:00:01.06

smpte_DNxHR_640x480_yuv422p10le_bt709_limited.mxf
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=640x480 -vf noise=alls=10:allf=t -c:v dnxhd -profile dnxhr_hqx -pix_fmt yuv422p10le -vf setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709 -color_range limited /home/adg/github/video-patterns/smpte_DNxHR_640x480_yuv422p10le_bt709_limited.mxf -y
frame=   50 fps=0.0 q=1.0 Lsize=    6656KiB time=00:00:02.00 bitrate=27263.2kbits/s speed=6.93x elapsed=0:00:00.28

smpte_ProRes_640x480_yuv422p10le_limited.mov
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=640x480 -vf noise=alls=10:allf=t -c:v prores_ks -profile 2 -pix_fmt yuv422p10le -color_range limited /home/adg/github/video-patterns/smpte_ProRes_640x480_yuv422p10le_limited.mov -y
frame=   50 fps= 38 q=-0.0 Lsize=    7491KiB time=00:00:02.00 bitrate=30681.1kbits/s speed=1.54x elapsed=0:00:01.30

smpte_h264_720x540_yuv420p_bt709_limited.mkv
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=720x540 -vf noise=alls=10:allf=t -c:v libx264 -pix_fmt yuv420p -x264-params colorspace=bt709:colorprim=bt709:transfer=bt709 -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range limited /home/adg/github/video-patterns/smpte_h264_720x540_yuv420p_bt709_limited.mkv -y
frame=   50 fps= 41 q=-1.0 Lsize=    1088KiB time=00:00:01.92 bitrate=4641.1kbits/s speed=1.57x elapsed=0:00:01.22

smpte_h265_720x540_yuv420p_bt709_limited.mkv
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=720x540 -vf noise=alls=10:allf=t -c:v libx265 -pix_fmt yuv420p -x265-params colorprim=bt709:transfer=bt709:colormatrix=bt709 -color_range limited /home/adg/github/video-patterns/smpte_h265_720x540_yuv420p_bt709_limited.mkv -y
frame=   50 fps=0.0 q=35.6 Lsize=      27KiB time=00:00:01.92 bitrate= 114.5kbits/s speed=2.36x elapsed=0:00:00.81

smpte_h265_720x540_yuv422p10le_bt709_limited.mkv
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=720x540 -vf noise=alls=10:allf=t -c:v libx265 -pix_fmt yuv422p10le -x265-params colorprim=bt709:transfer=bt709:colormatrix=bt709 -color_range limited /home/adg/github/video-patterns/smpte_h265_720x540_yuv422p10le_bt709_limited.mkv -y
frame=   50 fps= 46 q=35.7 Lsize=      31KiB time=00:00:01.92 bitrate= 132.8kbits/s speed=1.78x elapsed=0:00:01.07

smpte_DNxHR_720x540_yuv422p10le_bt709_limited.mxf
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=720x540 -vf noise=alls=10:allf=t -c:v dnxhd -profile dnxhr_hqx -pix_fmt yuv422p10le -vf setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709 -color_range limited /home/adg/github/video-patterns/smpte_DNxHR_720x540_yuv422p10le_bt709_limited.mxf -y
frame=   50 fps=0.0 q=1.0 Lsize=    8456KiB time=00:00:02.00 bitrate=34636.0kbits/s speed=6.95x elapsed=0:00:00.28

smpte_ProRes_720x540_yuv422p10le_limited.mov
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=720x540 -vf noise=alls=10:allf=t -c:v prores_ks -profile 2 -pix_fmt yuv422p10le -color_range limited /home/adg/github/video-patterns/smpte_ProRes_720x540_yuv422p10le_limited.mov -y
frame=   50 fps= 32 q=-0.0 Lsize=    9882KiB time=00:00:02.00 bitrate=40477.3kbits/s speed=1.29x elapsed=0:00:01.55

smpte_h264_720x576_yuv420p_bt709_limited.mkv
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=720x576 -vf noise=alls=10:allf=t -c:v libx264 -pix_fmt yuv420p -x264-params colorspace=bt709:colorprim=bt709:transfer=bt709 -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range limited /home/adg/github/video-patterns/smpte_h264_720x576_yuv420p_bt709_limited.mkv -y
frame=   50 fps= 34 q=-1.0 Lsize=    1275KiB time=00:00:01.92 bitrate=5438.7kbits/s speed=1.32x elapsed=0:00:01.45

smpte_h265_720x576_yuv420p_bt709_limited.mkv
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=720x576 -vf noise=alls=10:allf=t -c:v libx265 -pix_fmt yuv420p -x265-params colorprim=bt709:transfer=bt709:colormatrix=bt709 -color_range limited /home/adg/github/video-patterns/smpte_h265_720x576_yuv420p_bt709_limited.mkv -y
frame=   50 fps= 41 q=35.3 Lsize=      34KiB time=00:00:01.92 bitrate= 144.9kbits/s speed=1.57x elapsed=0:00:01.22

smpte_h265_720x576_yuv422p10le_bt709_limited.mkv
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=720x576 -vf noise=alls=10:allf=t -c:v libx265 -pix_fmt yuv422p10le -x265-params colorprim=bt709:transfer=bt709:colormatrix=bt709 -color_range limited /home/adg/github/video-patterns/smpte_h265_720x576_yuv422p10le_bt709_limited.mkv -y
frame=   50 fps= 44 q=35.8 Lsize=      40KiB time=00:00:01.92 bitrate= 169.5kbits/s speed=1.69x elapsed=0:00:01.13

smpte_DNxHR_720x576_yuv422p10le_bt709_limited.mxf
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=720x576 -vf noise=alls=10:allf=t -c:v dnxhd -profile dnxhr_hqx -pix_fmt yuv422p10le -vf setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709 -color_range limited /home/adg/github/video-patterns/smpte_DNxHR_720x576_yuv422p10le_bt709_limited.mxf -y
frame=   50 fps=0.0 q=1.0 Lsize=    8856KiB time=00:00:02.00 bitrate=36274.4kbits/s speed=6.84x elapsed=0:00:00.29

smpte_ProRes_720x576_yuv422p10le_limited.mov
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=720x576 -vf noise=alls=10:allf=t -c:v prores_ks -profile 2 -pix_fmt yuv422p10le -color_range limited /home/adg/github/video-patterns/smpte_ProRes_720x576_yuv422p10le_limited.mov -y
frame=   50 fps= 27 q=-0.0 Lsize=   10463KiB time=00:00:02.00 bitrate=42857.4kbits/s speed=1.08x elapsed=0:00:01.85

smpte_h264_1280x720_yuv420p_bt709_limited.mkv
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=1280x720 -vf noise=alls=10:allf=t -c:v libx264 -pix_fmt yuv420p -x264-params colorspace=bt709:colorprim=bt709:transfer=bt709 -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range limited /home/adg/github/video-patterns/smpte_h264_1280x720_yuv420p_bt709_limited.mkv -y
frame=   50 fps= 16 q=-1.0 Lsize=    2922KiB time=00:00:01.92 bitrate=12466.4kbits/s speed=0.616x elapsed=0:00:03.11

smpte_h265_1280x720_yuv420p_bt709_limited.mkv
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=1280x720 -vf noise=alls=10:allf=t -c:v libx265 -pix_fmt yuv420p -x265-params colorprim=bt709:transfer=bt709:colormatrix=bt709 -color_range limited /home/adg/github/video-patterns/smpte_h265_1280x720_yuv420p_bt709_limited.mkv -y
frame=   50 fps= 29 q=35.0 Lsize=      64KiB time=00:00:01.92 bitrate= 271.5kbits/s speed=1.12x elapsed=0:00:01.71

smpte_h265_1280x720_yuv422p10le_bt709_limited.mkv
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=1280x720 -vf noise=alls=10:allf=t -c:v libx265 -pix_fmt yuv422p10le -x265-params colorprim=bt709:transfer=bt709:colormatrix=bt709 -color_range limited /home/adg/github/video-patterns/smpte_h265_1280x720_yuv422p10le_bt709_limited.mkv -y
frame=   50 fps= 20 q=34.7 Lsize=      80KiB time=00:00:01.92 bitrate= 339.9kbits/s speed=0.766x elapsed=0:00:02.50

smpte_DNxHR_1280x720_yuv422p10le_bt709_limited.mxf
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=1280x720 -vf noise=alls=10:allf=t -c:v dnxhd -profile dnxhr_hqx -pix_fmt yuv422p10le -vf setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709 -color_range limited /home/adg/github/video-patterns/smpte_DNxHR_1280x720_yuv422p10le_bt709_limited.mxf -y
frame=   50 fps=0.0 q=1.0 Lsize=   19856KiB time=00:00:02.00 bitrate=81330.4kbits/s speed=3.63x elapsed=0:00:00.55

smpte_ProRes_1280x720_yuv422p10le_limited.mov
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=1280x720 -vf noise=alls=10:allf=t -c:v prores_ks -profile 2 -pix_fmt yuv422p10le -color_range limited /home/adg/github/video-patterns/smpte_ProRes_1280x720_yuv422p10le_limited.mov -y
frame=   50 fps= 12 q=-0.0 Lsize=   15252KiB time=00:00:02.00 bitrate=62472.0kbits/s speed=0.47x elapsed=0:00:04.25

smpte_h264_1920x1080_yuv420p_bt709_limited.mkv
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=1920x1080 -vf noise=alls=10:allf=t -c:v libx264 -pix_fmt yuv420p -x264-params colorspace=bt709:colorprim=bt709:transfer=bt709 -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range limited /home/adg/github/video-patterns/smpte_h264_1920x1080_yuv420p_bt709_limited.mkv -y
frame=   50 fps=8.6 q=-1.0 Lsize=    7096KiB time=00:00:01.92 bitrate=30274.5kbits/s speed=0.332x elapsed=0:00:05.78

smpte_h265_1920x1080_yuv420p_bt709_limited.mkv
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=1920x1080 -vf noise=alls=10:allf=t -c:v libx265 -pix_fmt yuv420p -x265-params colorprim=bt709:transfer=bt709:colormatrix=bt709 -color_range limited /home/adg/github/video-patterns/smpte_h265_1920x1080_yuv420p_bt709_limited.mkv -y
frame=   50 fps= 17 q=34.2 Lsize=     167KiB time=00:00:01.92 bitrate= 712.3kbits/s speed=0.659x elapsed=0:00:02.91

smpte_h265_1920x1080_yuv422p10le_bt709_limited.mkv
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=1920x1080 -vf noise=alls=10:allf=t -c:v libx265 -pix_fmt yuv422p10le -x265-params colorprim=bt709:transfer=bt709:colormatrix=bt709 -color_range limited /home/adg/github/video-patterns/smpte_h265_1920x1080_yuv422p10le_bt709_limited.mkv -y
frame=   50 fps= 13 q=35.4 Lsize=     212KiB time=00:00:01.92 bitrate= 904.8kbits/s speed=0.51x elapsed=0:00:03.76

smpte_DNxHR_1920x1080_yuv422p10le_bt709_limited.mxf
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=1920x1080 -vf noise=alls=10:allf=t -c:v dnxhd -profile dnxhr_hqx -pix_fmt yuv422p10le -vf setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709 -color_range limited /home/adg/github/video-patterns/smpte_DNxHR_1920x1080_yuv422p10le_bt709_limited.mxf -y
frame=   50 fps=0.0 q=1.0 Lsize=   44856KiB time=00:00:02.00 bitrate=183730.4kbits/s speed=2.31x elapsed=0:00:00.86

smpte_ProRes_1920x1080_yuv422p10le_limited.mov
ffmpeg -hide_banner -loglevel error -stats -f lavfi -i smptehdbars=rate=25:duration=2.0:size=1920x1080 -vf noise=alls=10:allf=t -c:v prores_ks -profile 2 -pix_fmt yuv422p10le -color_range limited /home/adg/github/video-patterns/smpte_ProRes_1920x1080_yuv422p10le_limited.mov -y
frame=   50 fps=5.2 q=-0.0 Lsize=   30669KiB time=00:00:02.00 bitrate=125620.5kbits/s speed=0.208x elapsed=0:00:09.59
