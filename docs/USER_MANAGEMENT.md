# HeySeen User Management System

## Tổng quan
HeySeen hiện đã được tích hợp hệ thống quản lý người dùng hoàn chỉnh sử dụng IndexedDB của trình duyệt web. Hệ thống cho phép quản lý thông tin người dùng, theo dõi các dự án đã chuyển đổi, và phân cấp quyền truy cập dựa trên vai trò người dùng.

## Tính năng chính

### 1. Quản lý người dùng
- **Lưu trữ cục bộ**: Tất cả thông tin người dùng được lưu trong IndexedDB của trình duyệt
- **Hồ sơ cá nhân**: Người dùng có thể cập nhật tên, email và avatar
- **Chuyển đổi tài khoản**: Hỗ trợ chuyển đổi giữa nhiều tài khoản khác nhau
- **Avatar tự động**: Hiển thị avatar với chữ cái đầu của tên người dùng

### 2. Phân cấp vai trò

#### Guest (Khách)
- Số trang tối đa: **1 trang**
- Dung lượng tối đa: **1 MB**
- Mặc định cho người dùng mới

#### Students (Sinh viên)
- Số trang tối đa: **10 trang**
- Dung lượng tối đa: **5 MB**

#### Masters (Thạc sĩ)
- Số trang tối đa: **20 trang**
- Dung lượng tối đa: **10 MB**

#### Lecturers (Giảng viên)
- Số trang tối đa: **50 trang**
- Dung lượng tối đa: **20 MB**

#### Professors (Giáo sư)
- Số trang tối đa: **100 trang**
- Dung lượng tối đa: **50 MB**

#### Experts (Chuyên gia)
- Số trang tối đa: **200 trang**
- Dung lượng tối đa: **100 MB**

### 3. Quản lý dự án
- **Lịch sử dự án**: Xem tất cả các dự án đã thực hiện
- **Trạng thái theo dõi**: Queued, Processing, Completed, Failed
- **Tải xuống**: Truy cập nhanh các dự án đã hoàn thành
- **Xóa dự án**: Quản lý và dọn dẹp các dự án cũ

### 4. Admin Panel (Quản trị viên)
**Tài khoản admin**: `nguyendangminhphuc@dhsphue.edu.vn`

#### Thống kê hệ thống:
- Tổng số người dùng
- Tổng số dự án
- Phân loại theo vai trò
- Phân loại theo trạng thái

#### Quản lý người dùng:
- Xem danh sách tất cả người dùng
- Nâng cấp/hạ cấp vai trò người dùng
- Xóa người dùng (trừ admin)
- Tìm kiếm người dùng

#### Quản lý dự án:
- Xem tất cả dự án của hệ thống
- Xóa dự án
- Tìm kiếm theo tên file hoặc email

## Cấu trúc Database

### Users Store
```javascript
{
  email: string (primary key),
  name: string,
  role: string,
  avatar: string,
  createdAt: number,
  lastLogin: number,
  projectCount: number
}
```

### Projects Store
```javascript
{
  id: string (primary key),
  userEmail: string,
  fileName: string,
  fileSize: number,
  status: string,
  progress: number,
  message: string,
  useMath: boolean,
  useLLM: boolean,
  downloadUrl: string,
  createdAt: number,
  completedAt: number
}
```

## Hướng dẫn sử dụng

### Đối với người dùng thông thường:

1. **Lần đầu sử dụng**:
   - Hệ thống tự động tạo tài khoản Guest
   - Click vào avatar góc trên phải để xem thông tin

2. **Cập nhật hồ sơ**:
   - Click avatar → "My Profile"
   - Nhập tên và email
   - Click "Save Profile"

3. **Chuyển đổi tài khoản**:
   - Click avatar → "Switch Account"
   - Nhập email (tạo mới hoặc đăng nhập)

4. **Xem dự án**:
   - Click avatar → "My Projects"
   - Xem lịch sử, tải xuống hoặc xóa dự án

5. **Upload file**:
   - Hệ thống tự động kiểm tra giới hạn theo vai trò
   - Thông báo lỗi nếu vượt quá giới hạn

### Đối với Admin:

1. **Truy cập Admin Panel**:
   - Đăng nhập với email admin
   - Click avatar → "Admin Panel"

2. **Xem thống kê**:
   - Tab "Statistics" hiển thị tổng quan hệ thống

3. **Quản lý người dùng**:
   - Tab "Users" để xem và chỉnh sửa
   - Thay đổi role trực tiếp trong bảng
   - Xóa người dùng không mong muốn

4. **Quản lý dự án**:
   - Tab "All Projects" để xem tất cả dự án
   - Xóa các dự án lỗi hoặc không cần thiết

## Tính năng bổ sung

### 1. Validation tự động
- Kiểm tra dung lượng file trước khi upload
- Kiểm tra số trang PDF (sau khi load)
- Hiển thị thông báo rõ ràng về giới hạn

### 2. Persistent Storage
- Dữ liệu được lưu vĩnh viễn trong trình duyệt
- Không bị mất khi đóng/mở lại tab
- Mỗi trình duyệt có database riêng

### 3. User Experience
- Avatar màu sắc gradient đẹp mắt
- Badge vai trò với màu sắc phân biệt
- Dropdown menu trực quan
- Modal hiện đại, responsive

### 4. Security Features
- Admin account được hard-code
- Không thể xóa tài khoản admin
- Validation email format
- Xác nhận trước khi xóa

## File mới được tạo

1. **`db.js`**: IndexedDB manager
   - Khởi tạo database
   - CRUD operations cho users và projects
   - Validation và statistics

2. **`app.js`**: Application logic
   - UI management
   - Event handlers
   - Modal controls
   - Admin functions

3. **`index.html`** (updated): UI components
   - Header với avatar
   - Modals: Profile, Projects, Admin, Switch User
   - Responsive design với Tailwind CSS

## Khởi chạy

Không cần cấu hình gì thêm. Hệ thống tự động khởi tạo khi trang web được tải:

```bash
cd /Users/m2pro/HeySeen
./start.sh
```

Truy cập: `http://localhost:5555` hoặc URL của Cloudflare Tunnel

## Lưu ý quan trọng

1. **Data là client-side**: 
   - Dữ liệu lưu trong trình duyệt của từng người dùng
   - Không đồng bộ giữa các thiết bị/trình duyệt
   - Clear cache/data sẽ mất thông tin

2. **Admin access**:
   - Chỉ có một admin account
   - Thay đổi email admin trong file `db.js` nếu cần

3. **Role limits**:
   - Có thể điều chỉnh trong `db.js` (USER_ROLES constant)
   - Thay đổi sẽ áp dụng ngay lập tức

4. **Browser compatibility**:
   - Yêu cầu trình duyệt hỗ trợ IndexedDB
   - Tốt nhất với Chrome, Firefox, Safari, Edge hiện đại

## Tương lai

Có thể mở rộng:
- Sync với backend server (optional)
- Export/Import user data
- Statistics dashboard chi tiết hơn
- Notification system
- Project sharing giữa users
- Payment integration cho premium roles

## Troubleshooting

### Database không khởi tạo:
```javascript
// Mở Console và kiểm tra:
indexedDB.databases()
```

### Reset database:
```javascript
// Trong Console:
indexedDB.deleteDatabase('HeySeenDB')
location.reload()
```

### Kiểm tra user hiện tại:
```javascript
// Trong Console:
dbManager.getCurrentUser().then(console.log)
```

## Liên hệ

Mọi thắc mắc hoặc đề xuất tính năng, vui lòng liên hệ:
- Email: ndmphuc@hueuni.edu.vn
- GitHub: [phucdhh/HeySeen](https://github.com/phucdhh/HeySeen)
