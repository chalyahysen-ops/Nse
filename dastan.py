using MySql.Data.MySqlClient;
using System;
using System.Collections.Generic;
using System.Data;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Windows.Forms;

namespace ShahurRestaurant
{
    public partial class OrderForm : Form
    {
        private int tableNumber;
        private DataTable orderTable;
        private readonly CultureInfo enCulture = CultureInfo.InvariantCulture;

        // ڕەنگە سەرەکییەکان (Luxury POS Theme)
        private Color colorDarkBg = Color.FromArgb(10, 15, 29);
        private Color colorTableBg = Color.FromArgb(15, 23, 42);
        private Color colorRowAlt = Color.FromArgb(18, 28, 50);
        private Color colorGold = Color.FromArgb(245, 158, 11);
        private Color colorGreen = Color.FromArgb(16, 185, 129);
        private Color colorRed = Color.FromArgb(239, 68, 68);
        private Color colorBorder = Color.FromArgb(30, 58, 138);

        // کۆنتڕۆڵی خوارەوە (پەنێڵی برنج، مریشک و قاپی نوێ)
        private Panel pnlControlBox;
        private Label lblSelectedFoodTitle;
        private Label lblR;
        private Label lblC;
        private ComboBox cmbBoxRice;
        private ComboBox cmbBoxChicken;
        private Button btnAddPlateDivider;
        private int currentSelectedRowIndex = -1;
        private bool isUpdatingSelection = false;

        public OrderForm(int tableNum)
        {
            InitializeComponent();
            this.tableNumber = tableNum;
            lblTableNumber.Text = tableNumber.ToString(enCulture);
        }

        private void OrderForm_Load(object sender, EventArgs e)
        {
            this.WindowState = FormWindowState.Maximized;

            ApplyRabarFont();
            SetupOrderGrid();
            CreateBottomControlBox(); 
            LoadSidebarCategories();
            LoadCategoryFoods("هەموو");
            LoadExistingOrders();
        }

        private void ApplyRabarFont()
        {
            Font fontTitle = new Font("Noto Kufi Arabic", 14F, FontStyle.Bold);

            this.BackColor = colorDarkBg;
            lblTableTitle.Font = fontTitle;
            lblTableTitle.ForeColor = Color.White;

            lblTableNumber.Font = new Font("Segoe UI", 20F, FontStyle.Bold);
            lblTableNumber.ForeColor = colorGold;

            lblTotal.Font = new Font("Segoe UI", 16F, FontStyle.Bold);
            lblTotal.ForeColor = colorGreen;
        }

        private void CreateBottomControlBox()
        {
            pnlControlBox = new Panel
            {
                Dock = DockStyle.Bottom,
                Height = 52,
                BackColor = Color.FromArgb(15, 23, 42),
                Padding = new Padding(8),
                Visible = false
            };

            pnlControlBox.Paint += (s, e) => {
                ControlPaint.DrawBorder(e.Graphics, pnlControlBox.ClientRectangle, colorGold, ButtonBorderStyle.Solid);
            };

            lblSelectedFoodTitle = new Label
            {
                Text = "خواردن: -",
                ForeColor = colorGreen,
                Font = new Font("Noto Kufi Arabic", 10F, FontStyle.Bold),
                Location = new Point(15, 14),
                AutoSize = true
            };

            lblR = new Label { Text = "جۆری برنج:", ForeColor = Color.White, Font = new Font("Noto Kufi Arabic", 9F, FontStyle.Regular), Location = new Point(260, 15), AutoSize = true };
            cmbBoxRice = new ComboBox
            {
                Location = new Point(330, 12),
                Width = 115,
                Font = new Font("Noto Kufi Arabic", 9F, FontStyle.Regular),
                DropDownStyle = ComboBoxStyle.DropDownList
            };
            cmbBoxRice.Items.AddRange(new string[] { "", "برنجی درێژ", "برنجی خڕ", "برنجی کوردی", "برنج بە سرکە" });
            cmbBoxRice.SelectedIndexChanged += CmbBoxRice_SelectedIndexChanged;

            lblC = new Label { Text = "بەشی مریشک:", ForeColor = Color.White, Font = new Font("Noto Kufi Arabic", 9F, FontStyle.Regular), Location = new Point(455, 15), AutoSize = true };
            cmbBoxChicken = new ComboBox
            {
                Location = new Point(535, 12),
                Width = 90,
                Font = new Font("Noto Kufi Arabic", 9F, FontStyle.Regular),
                DropDownStyle = ComboBoxStyle.DropDownList
            };
            cmbBoxChicken.Items.AddRange(new string[] { "", "سینگ", "ڕان" });
            cmbBoxChicken.SelectedIndexChanged += CmbBoxChicken_SelectedIndexChanged;

            btnAddPlateDivider = new Button
            {
                Text = "➕ قاپی نوێ (برژاو)",
                Location = new Point(330, 10),
                Size = new Size(160, 32),
                BackColor = Color.FromArgb(139, 92, 246),
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Noto Kufi Arabic", 9.5F, FontStyle.Bold),
                Cursor = Cursors.Hand,
                Visible = false 
            };
            btnAddPlateDivider.FlatAppearance.BorderSize = 0;
            btnAddPlateDivider.Click += BtnAddPlateDivider_Click;

            pnlControlBox.Controls.Add(lblSelectedFoodTitle);
            pnlControlBox.Controls.Add(lblR);
            pnlControlBox.Controls.Add(cmbBoxRice);
            pnlControlBox.Controls.Add(lblC);
            pnlControlBox.Controls.Add(cmbBoxChicken);
            pnlControlBox.Controls.Add(btnAddPlateDivider);

            this.Controls.Add(pnlControlBox);
            pnlControlBox.BringToFront();
        }

        private void BtnAddPlateDivider_Click(object sender, EventArgs e)
        {
            orderTable.Rows.Add("برژاو", "--- قاپی نوێ ---", "", "", 0, 0, 1);
        }

        private void SetupOrderGrid()
        {
            orderTable = new DataTable();
            orderTable.Columns.Add("category", typeof(string));
            orderTable.Columns.Add("ناوی خواردن", typeof(string));
            orderTable.Columns.Add("جۆری برنج", typeof(string));
            orderTable.Columns.Add("بەشی مریشک", typeof(string));
            orderTable.Columns.Add("نرخی خواردن", typeof(decimal));
            orderTable.Columns.Add("کۆی گشتی", typeof(decimal));
            orderTable.Columns.Add("عدد", typeof(int));

            dgvOrder.DataSource = orderTable;
            dgvOrder.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;

            dgvOrder.AllowUserToAddRows = false;
            dgvOrder.AllowUserToDeleteRows = false;
            dgvOrder.MultiSelect = false;

            if (dgvOrder.Columns.Contains("category"))
                dgvOrder.Columns["category"].Visible = false;

            if (dgvOrder.Columns.Contains("جۆری برنج"))
                dgvOrder.Columns["جۆری برنج"].Visible = false;

            if (dgvOrder.Columns.Contains("بەشی مریشک"))
                dgvOrder.Columns["بەشی مریشک"].Visible = false;

            if (dgvOrder.Columns.Contains("نرخی خواردن"))
                dgvOrder.Columns["نرخی خواردن"].Visible = false;

            dgvOrder.RowHeadersVisible = false;
            dgvOrder.BackgroundColor = colorTableBg;
            dgvOrder.BorderStyle = BorderStyle.FixedSingle;
            dgvOrder.CellBorderStyle = DataGridViewCellBorderStyle.Single;
            dgvOrder.GridColor = colorBorder;

            dgvOrder.EnableHeadersVisualStyles = false;
            dgvOrder.ColumnHeadersDefaultCellStyle.BackColor = Color.FromArgb(8, 12, 24);
            dgvOrder.ColumnHeadersDefaultCellStyle.ForeColor = colorGold;
            dgvOrder.ColumnHeadersDefaultCellStyle.Font = new Font("Noto Kufi Arabic", 11F, FontStyle.Bold);
            dgvOrder.ColumnHeadersDefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter;
            dgvOrder.ColumnHeadersHeight = 50;

            dgvOrder.DefaultCellStyle.BackColor = colorTableBg;
            dgvOrder.AlternatingRowsDefaultCellStyle.BackColor = colorRowAlt;
            dgvOrder.DefaultCellStyle.ForeColor = Color.White;
            
            dgvOrder.DefaultCellStyle.SelectionBackColor = Color.FromArgb(6, 95, 70);
            dgvOrder.DefaultCellStyle.SelectionForeColor = Color.White;
            dgvOrder.DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter;
            dgvOrder.RowTemplate.Height = 55;

            dgvOrder.Columns["ناوی خواردن"].FillWeight = 180;
            dgvOrder.Columns["ناوی خواردن"].DefaultCellStyle.Font = new Font("Noto Kufi Arabic", 11.5F, FontStyle.Bold);

            dgvOrder.Columns["کۆی گشتی"].FillWeight = 110;
            dgvOrder.Columns["کۆی گشتی"].DefaultCellStyle.Font = new Font("Segoe UI", 12F, FontStyle.Bold);
            dgvOrder.Columns["کۆی گشتی"].DefaultCellStyle.FormatProvider = enCulture;
            dgvOrder.Columns["کۆی گشتی"].DefaultCellStyle.Format = "N0";

            dgvOrder.Columns["عدد"].FillWeight = 50;
            dgvOrder.Columns["عدد"].DefaultCellStyle.Font = new Font("Segoe UI", 13.5F, FontStyle.Bold);
            dgvOrder.Columns["عدد"].DefaultCellStyle.FormatProvider = enCulture;
            dgvOrder.Columns["عدد"].DefaultCellStyle.Format = "N0";

            if (!dgvOrder.Columns.Contains("btnPlus"))
            {
                DataGridViewButtonColumn btnPlus = new DataGridViewButtonColumn();
                btnPlus.Name = "btnPlus"; btnPlus.HeaderText = "+"; btnPlus.Text = "+";
                btnPlus.UseColumnTextForButtonValue = true; btnPlus.FillWeight = 45; btnPlus.FlatStyle = FlatStyle.Flat;
                dgvOrder.Columns.Add(btnPlus);
            }

            if (!dgvOrder.Columns.Contains("btnMinus"))
            {
                DataGridViewButtonColumn btnMinus = new DataGridViewButtonColumn();
                btnMinus.Name = "btnMinus"; btnMinus.HeaderText = "-"; btnMinus.Text = "-";
                btnMinus.UseColumnTextForButtonValue = true; btnMinus.FillWeight = 45; btnMinus.FlatStyle = FlatStyle.Flat;
                dgvOrder.Columns.Add(btnMinus);
            }

            if (!dgvOrder.Columns.Contains("btnDelete"))
            {
                DataGridViewButtonColumn btnDelete = new DataGridViewButtonColumn();
                btnDelete.Name = "btnDelete"; btnDelete.HeaderText = "X"; btnDelete.Text = "X";
                btnDelete.UseColumnTextForButtonValue = true; btnDelete.FillWeight = 48; btnDelete.FlatStyle = FlatStyle.Flat;
                dgvOrder.Columns.Add(btnDelete);
            }

            dgvOrder.CellFormatting += DgvOrder_CellFormatting;
            dgvOrder.CellClick += DgvOrder_CellClick;
        }

        private void DgvOrder_CellClick(object sender, DataGridViewCellEventArgs e)
        {
            if (e.RowIndex >= 0 && e.RowIndex < orderTable.Rows.Count)
            {
                currentSelectedRowIndex = e.RowIndex;
                DataRow row = orderTable.Rows[e.RowIndex];
                string foodName = row["ناوی خواردن"].ToString();
                string cat = row["category"] != DBNull.Value ? row["category"].ToString() : "";
                string rice = row["جۆری برنج"] != DBNull.Value ? row["جۆری برنج"].ToString() : "";
                string chicken = row["بەشی مریشک"] != DBNull.Value ? row["بەشی مریشک"].ToString() : "";

                if (foodName.Contains("--- قاپی نوێ ---"))
                {
                    pnlControlBox.Visible = false;
                    return;
                }

                bool needRice = (cat == "کوڵاو" || cat == "پەلەوەر" || cat == "کوردیەکان");
                bool needChicken = (cat == "پەلەوەر");
                bool isGrill = (cat == "برژاو");

                if (!needRice && !needChicken && !isGrill)
                {
                    pnlControlBox.Visible = false;
                    return;
                }

                isUpdatingSelection = true;
                pnlControlBox.Visible = true;
                lblSelectedFoodTitle.Text = $"خواردن: {foodName}";

                lblR.Visible = needRice;
                cmbBoxRice.Visible = needRice;
                lblC.Visible = needChicken;
                cmbBoxChicken.Visible = needChicken;
                btnAddPlateDivider.Visible = isGrill;

                if (needRice)
                {
                    cmbBoxRice.SelectedItem = string.IsNullOrEmpty(rice) ? null : rice;
                }
                if (needChicken)
                {
                    cmbBoxChicken.SelectedItem = string.IsNullOrEmpty(chicken) ? null : chicken;
                }

                isUpdatingSelection = false;
            }
        }

        private void CmbBoxRice_SelectedIndexChanged(object sender, EventArgs e)
        {
            if (!isUpdatingSelection && currentSelectedRowIndex >= 0 && currentSelectedRowIndex < orderTable.Rows.Count)
            {
                orderTable.Rows[currentSelectedRowIndex]["جۆری برنج"] = cmbBoxRice.SelectedItem?.ToString() ?? "";
            }
        }

        private void CmbBoxChicken_SelectedIndexChanged(object sender, EventArgs e)
        {
            if (!isUpdatingSelection && currentSelectedRowIndex >= 0 && currentSelectedRowIndex < orderTable.Rows.Count)
            {
                orderTable.Rows[currentSelectedRowIndex]["بەشی مریشک"] = cmbBoxChicken.SelectedItem?.ToString() ?? "";
            }
        }

        private void DgvOrder_CellFormatting(object sender, DataGridViewCellFormattingEventArgs e)
        {
            if (orderTable == null || e.RowIndex < 0 || e.RowIndex >= orderTable.Rows.Count)
                return;

            try
            {
                string colName = dgvOrder.Columns[e.ColumnIndex].Name;
                DataRow row = orderTable.Rows[e.RowIndex];
                string foodName = row["ناوی خواردن"].ToString();

                if (foodName.Contains("--- قاپی نوێ ---"))
                {
                    e.CellStyle.BackColor = Color.FromArgb(109, 40, 217);
                    e.CellStyle.ForeColor = Color.White;
                    e.CellStyle.Font = new Font("Noto Kufi Arabic", 11F, FontStyle.Bold);
                }

                if (colName == "btnPlus")
                {
                    e.CellStyle.ForeColor = colorGreen; 
                    e.CellStyle.Font = new Font("Segoe UI", 20F, FontStyle.Bold);
                }
                else if (colName == "btnMinus")
                {
                    e.CellStyle.ForeColor = colorGold; 
                    e.CellStyle.Font = new Font("Segoe UI", 20F, FontStyle.Bold);
                }
                else if (colName == "btnDelete")
                {
                    e.CellStyle.ForeColor = colorRed; 
                    e.CellStyle.Font = new Font("Segoe UI", 16F, FontStyle.Bold);
                }
                else if (colName == "کۆی گشتی")
                {
                    e.CellStyle.ForeColor = Color.FromArgb(52, 211, 153);
                    e.CellStyle.Font = new Font("Segoe UI", 12F, FontStyle.Bold);
                    if (e.Value != null && decimal.TryParse(e.Value.ToString(), out decimal val))
                    {
                        e.Value = val.ToString("N0", enCulture);
                        e.FormattingApplied = true;
                    }
                }
                else if (colName == "عدد")
                {
                    e.CellStyle.ForeColor = colorGold; 
                    e.CellStyle.Font = new Font("Segoe UI", 13.5F, FontStyle.Bold);
                    if (e.Value != null && int.TryParse(e.Value.ToString(), out int val))
                    {
                        e.Value = val.ToString(enCulture);
                        e.FormattingApplied = true;
                    }
                }
            }
            catch { }
        }

        private void LoadSidebarCategories()
        {
            flowCategories.Controls.Clear();
            AddCategorySidebarButton("هەموو", "🍚");

            try
            {
                using (MySqlConnection conn = Database.GetConnection())
                {
                    if (conn.State == ConnectionState.Closed) conn.Open();
                    string query = "SELECT DISTINCT category FROM nse WHERE category IS NOT NULL AND category != ''";
                    using (MySqlCommand cmd = new MySqlCommand(query, conn))
                    {
                        using (MySqlDataReader reader = cmd.ExecuteReader())
                        {
                            while (reader.Read())
                            {
                                AddCategorySidebarButton(reader["category"].ToString(), "🍽");
                            }
                        }
                    }
                }
            }
            catch { }
        }

        private void AddCategorySidebarButton(string catName, string icon)
        {
            Button btn = new Button
            {
                Text = $"{icon}  {catName}",
                Size = new Size(130, 42),
                Margin = new Padding(3),
                BackColor = colorGold,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Noto Kufi Arabic", 9.5F, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            btn.FlatAppearance.BorderSize = 0;
            btn.Click += (s, e) => {
                lblMenuHeader.Text = $"⟵ {catName} ⟶";
                LoadCategoryFoods(catName);
            };
            flowCategories.Controls.Add(btn);
        }

        private void LoadCategoryFoods(string categoryName)
        {
            flowMenuPanel.Controls.Clear();

            try
            {
                using (MySqlConnection conn = Database.GetConnection())
                {
                    if (conn.State == ConnectionState.Closed) conn.Open();

                    string query = categoryName == "هەموو"
                        ? "SELECT food_name, price, image_path, category FROM nse"
                        : "SELECT food_name, price, image_path, category FROM nse WHERE category = @cat";

                    using (MySqlCommand cmd = new MySqlCommand(query, conn))
                    {
                        if (categoryName != "هەموو") cmd.Parameters.AddWithValue("@cat", categoryName);

                        using (MySqlDataReader reader = cmd.ExecuteReader())
                        {
                            while (reader.Read())
                            {
                                string fName = reader["food_name"].ToString();
                                decimal fPrice = Convert.ToDecimal(reader["price"]);
                                string imgPath = reader["image_path"].ToString();
                                string fCat = reader["category"] != DBNull.Value ? reader["category"].ToString() : "";

                                Panel card = new Panel
                                {
                                    Size = new Size(142, 150),
                                    Margin = new Padding(6),
                                    BackColor = Color.White,
                                    Cursor = Cursors.Hand
                                };

                                Label lblName = new Label
                                {
                                    Text = fName,
                                    Dock = DockStyle.Top,
                                    Height = 30,
                                    TextAlign = ContentAlignment.MiddleCenter,
                                    Font = new Font("Noto Kufi Arabic", 8.5F, FontStyle.Bold),
                                    ForeColor = Color.FromArgb(15, 23, 42)
                                };

                                Label lblPrice = new Label
                                {
                                    Text = fPrice.ToString("N0", enCulture),
                                    Dock = DockStyle.Bottom,
                                    Height = 24,
                                    TextAlign = ContentAlignment.MiddleCenter,
                                    Font = new Font("Segoe UI", 10F, FontStyle.Bold),
                                    ForeColor = Color.FromArgb(15, 23, 42),
                                    BackColor = colorGold
                                };

                                PictureBox pic = new PictureBox
                                {
                                    Dock = DockStyle.Fill,
                                    SizeMode = PictureBoxSizeMode.Zoom,
                                    BackColor = Color.White
                                };

                                if (!string.IsNullOrEmpty(imgPath))
                                {
                                    try
                                    {
                                        if (imgPath.StartsWith("http", StringComparison.OrdinalIgnoreCase))
                                            pic.LoadAsync(imgPath);
                                        else if (File.Exists(imgPath))
                                            pic.Image = Image.FromFile(imgPath);
                                    }
                                    catch { }
                                }

                                card.Controls.Add(pic);
                                card.Controls.Add(lblName);
                                card.Controls.Add(lblPrice);

                                Action addFoodAction = () => AddToOrder(fName, fPrice, fCat);
                                card.Click += (s, e) => addFoodAction();
                                lblName.Click += (s, e) => addFoodAction();
                                lblPrice.Click += (s, e) => addFoodAction();
                                pic.Click += (s, e) => addFoodAction();

                                flowMenuPanel.Controls.Add(card);
                            }
                        }
                    }
                }
            }
            catch { }
        }

        private void AddToOrder(string foodName, decimal price, string category = "")
        {
            if (!foodName.Contains("--- قاپی نوێ ---"))
            {
                foreach (DataRow row in orderTable.Rows)
                {
                    string existingName = row["ناوی خواردن"].ToString();
                    if (existingName == foodName)
                    {
                        int qty = Convert.ToInt32(row["عدد"]) + 1;
                        row["عدد"] = qty;
                        row["کۆی گشتی"] = qty * price;
                        CalculateTotal();
                        return;
                    }
                }
            }

            string defaultRice = "";
            string defaultChicken = "";

            orderTable.Rows.Add(category, foodName, defaultRice, defaultChicken, price, price, 1);
            CalculateTotal();
        }

        private void CalculateTotal()
        {
            decimal total = 0;
            foreach (DataRow row in orderTable.Rows)
            {
                string name = row["ناوی خواردن"] != DBNull.Value ? row["ناوی خواردن"].ToString() : "";
                if (!name.Contains("--- قاپی نوێ ---"))
                {
                    total += Convert.ToDecimal(row["کۆی گشتی"]);
                }
            }
            lblTotal.Text = "کۆی گشتی: " + total.ToString("N0", enCulture) + " IQD";
        }

        private void LoadExistingOrders()
        {
            try
            {
                using (MySqlConnection conn = Database.GetConnection())
                {
                    if (conn.State == ConnectionState.Closed) conn.Open();

                    string query = "SELECT food_name, category, SUM(quantity) AS total_qty, price FROM froshtn WHERE table_cabin = @tbl GROUP BY food_name, category, price";
                    using (MySqlCommand cmd = new MySqlCommand(query, conn))
                    {
                        cmd.Parameters.AddWithValue("@tbl", tableNumber.ToString(enCulture));
                        using (MySqlDataReader reader = cmd.ExecuteReader())
                        {
                            orderTable.Rows.Clear();
                            while (reader.Read())
                            {
                                string fullName = reader["food_name"].ToString();
                                string cat = reader["category"] != DBNull.Value ? reader["category"].ToString() : "";
                                int qty = Convert.ToInt32(reader["total_qty"]);
                                decimal price = Convert.ToDecimal(reader["price"]);

                                if (fullName.Contains("--- قاپی نوێ ---"))
                                {
                                    orderTable.Rows.Add(cat, fullName, "", "", 0, 0, 1);
                                    continue;
                                }

                                string rType = "";
                                string cPart = "";

                                foreach (var r in new[] { "برنجی درێژ", "برنجی خڕ", "برنجی کوردی", "برنج بە سرکە" })
                                {
                                    if (fullName.Contains($"({r})"))
                                    {
                                        rType = r;
                                        fullName = fullName.Replace($" ({r})", "").Trim();
                                        break;
                                    }
                                }

                                foreach (var c in new[] { "سینگ", "ڕان" })
                                {
                                    if (fullName.Contains($"({c})"))
                                    {
                                        cPart = c;
                                        fullName = fullName.Replace($" ({c})", "").Trim();
                                        break;
                                    }
                                }

                                orderTable.Rows.Add(cat, fullName, rType, cPart, price, qty * price, qty);
                            }
                            CalculateTotal();
                        }
                    }
                }
            }
            catch { }
        }

        private void dgvOrder_CellContentClick(object sender, DataGridViewCellEventArgs e)
        {
            if (e.RowIndex >= 0)
            {
                string colName = dgvOrder.Columns[e.ColumnIndex].Name;
                DataRow row = orderTable.Rows[e.RowIndex];
                string foodName = row["ناوی خواردن"].ToString();

                if (colName == "btnPlus")
                {
                    if (!foodName.Contains("--- قاپی نوێ ---"))
                    {
                        int currentQty = Convert.ToInt32(row["عدد"]);
                        decimal price = Convert.ToDecimal(row["نرخی خواردن"]);
                        row["عدد"] = currentQty + 1;
                        row["کۆی گشتی"] = (currentQty + 1) * price;
                        CalculateTotal();
                    }
                }
                else if (colName == "btnMinus")
                {
                    if (!foodName.Contains("--- قاپی نوێ ---"))
                    {
                        int currentQty = Convert.ToInt32(row["عدد"]);
                        decimal price = Convert.ToDecimal(row["نرخی خواردن"]);
                        if (currentQty > 1)
                        {
                            row["عدد"] = currentQty - 1;
                            row["کۆی گشتی"] = (currentQty - 1) * price;
                        }
                        else
                        {
                            orderTable.Rows.RemoveAt(e.RowIndex);
                            pnlControlBox.Visible = false;
                        }
                        CalculateTotal();
                    }
                    else
                    {
                        orderTable.Rows.RemoveAt(e.RowIndex);
                        pnlControlBox.Visible = false;
                    }
                }
                else if (colName == "btnDelete")
                {
                    orderTable.Rows.RemoveAt(e.RowIndex);
                    pnlControlBox.Visible = false;
                    CalculateTotal();
                }
            }
        }

        private void btnSendOrder_Click(object sender, EventArgs e)
        {
            if (orderTable.Rows.Count == 0)
            {
                MessageBox.Show("تکایە سەرەتا خواردنەکان هەڵبژێرە!", "ئاگاداری", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            try
            {
                using (MySqlConnection conn = Database.GetConnection())
                {
                    if (conn.State == ConnectionState.Closed) conn.Open();

                    string delQuery = "DELETE FROM froshtn WHERE table_cabin = @tbl";
                    using (MySqlCommand cmdDel = new MySqlCommand(delQuery, conn))
                    {
                        cmdDel.Parameters.AddWithValue("@tbl", tableNumber.ToString(enCulture));
                        cmdDel.ExecuteNonQuery();
                    }

                    foreach (DataRow row in orderTable.Rows)
                    {
                        string fName = row["ناوی خواردن"].ToString();
                        int qty = Convert.ToInt32(row["عدد"]);
                        decimal price = Convert.ToDecimal(row["نرخی خواردن"]);
                        string cat = row["category"] != null ? row["category"].ToString() : "";
                        string riceType = row["جۆری برنج"] != null ? row["جۆری برنج"].ToString() : "";
                        string chickenPart = row["بەشی مریشک"] != null ? row["بەشی مریشک"].ToString() : "";

                        string finalFoodName = fName;
                        if (!fName.Contains("--- قاپی نوێ ---"))
                        {
                            if ((cat == "کوڵاو" || cat == "پەلەوەر" || cat == "کوردیەکان") && !string.IsNullOrEmpty(riceType))
                            {
                                finalFoodName += $" ({riceType})";
                            }
                            if (cat == "پەلەوەر" && !string.IsNullOrEmpty(chickenPart))
                            {
                                finalFoodName += $" ({chickenPart})";
                            }
                        }

                        string insertQuery = @"INSERT INTO froshtn (table_cabin, food_name, quantity, price, category, created_at, is_printed) 
                                               VALUES (@tbl, @name, @qty, @price, @cat, NOW(), 0)";
                        using (MySqlCommand cmdInsert = new MySqlCommand(insertQuery, conn))
                        {
                            cmdInsert.Parameters.AddWithValue("@tbl", tableNumber.ToString(enCulture));
                            cmdInsert.Parameters.AddWithValue("@name", finalFoodName);
                            cmdInsert.Parameters.AddWithValue("@qty", qty);
                            cmdInsert.Parameters.AddWithValue("@price", price);
                            cmdInsert.Parameters.AddWithValue("@cat", cat);
                            cmdInsert.ExecuteNonQuery();
                        }

                        if (!fName.Contains("--- قاپی نوێ ---"))
                        {
                            string queryTomar = @"INSERT INTO tomar (record_date, food_name, quantity, total_price) 
                                                  VALUES (CURDATE(), @name, @qty, @total)
                                                  ON DUPLICATE KEY UPDATE 
                                                      quantity = quantity + VALUES(quantity),
                                                      total_price = total_price + VALUES(total_price)";
                            using (MySqlCommand cmdTomar = new MySqlCommand(queryTomar, conn))
                            {
                                cmdTomar.Parameters.AddWithValue("@name", finalFoodName);
                                cmdTomar.Parameters.AddWithValue("@qty", qty);
                                cmdTomar.Parameters.AddWithValue("@total", qty * price);
                                cmdTomar.ExecuteNonQuery();
                            }
                        }
                    }
                }

                KitchenPrintService.CheckAndPrintNewOrders();

                MessageBox.Show("داواکاریەکە بە سەرکەوتوویی تۆمارکرا و نێردرا بۆ مەتبەخ!", "سەرکەوتوو", MessageBoxButtons.OK, MessageBoxIcon.Information);
                this.Close();
            }
            catch (Exception ex)
            {
                MessageBox.Show("کێشە لە پاشەکەوتکردن و چاپ: " + ex.Message, "هەڵە", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void btnClearTable_Click(object sender, EventArgs e)
        {
            DialogResult result = MessageBox.Show("ئایا دڵنیایت لە سڕینەوەی سەرجەم داواکارییەکانی ئەم مێزە؟", "ئاگاداری", MessageBoxButtons.YesNo, MessageBoxIcon.Warning);
            if (result == DialogResult.Yes)
            {
                try
                {
                    using (MySqlConnection conn = Database.GetConnection())
                    {
                        if (conn.State == ConnectionState.Closed) conn.Open();
                        string deleteQuery = "DELETE FROM froshtn WHERE table_cabin = @tbl";
                        using (MySqlCommand cmd = new MySqlCommand(deleteQuery, conn))
                        {
                            cmd.Parameters.AddWithValue("@tbl", tableNumber.ToString(enCulture));
                            cmd.ExecuteNonQuery();
                        }
                    }

                    orderTable.Rows.Clear();
                    pnlControlBox.Visible = false;
                    CalculateTotal();
                    MessageBox.Show("مێزەکە بە سەرکەوتوویی پاککرایەوە.", "سەرکەوتوو", MessageBoxButtons.OK, MessageBoxIcon.Information);
                }
                catch (Exception ex)
                {
                    MessageBox.Show("هەڵە لە سڕینەوەی مێز: " + ex.Message, "هەڵە", MessageBoxButtons.OK, MessageBoxIcon.Error);
                }
            }
        }

        private void btnTableChange_Click(object sender, EventArgs e)
        {
            Form prompt = new Form()
            {
                Width = 350,
                Height = 200,
                FormBorderStyle = FormBorderStyle.FixedDialog,
                Text = "گۆڕانکاری مێز",
                StartPosition = FormStartPosition.CenterScreen,
                RightToLeft = RightToLeft.Yes,
                RightToLeftLayout = true,
                BackColor = colorDarkBg
            };

            Label textLabel = new Label() { Left = 20, Top = 20, Text = "ژمارەی مێزە نوێیەکە بنووسە:", AutoSize = true, Font = new Font("Noto Kufi Arabic", 10F, FontStyle.Bold), ForeColor = Color.White };
            TextBox textBox = new TextBox() { Left = 20, Top = 50, Width = 290, Font = new Font("Segoe UI", 12F, FontStyle.Bold), Text = tableNumber.ToString(enCulture) };
            Button confirmation = new Button() { Text = "پاشەکەوتکردن", Left = 180, Width = 130, Top = 90, Height = 40, DialogResult = DialogResult.OK, Font = new Font("Noto Kufi Arabic", 10F, FontStyle.Bold), BackColor = colorGreen, ForeColor = Color.White, FlatStyle = FlatStyle.Flat };

            prompt.Controls.Add(textBox);
            prompt.Controls.Add(confirmation);
            prompt.Controls.Add(textLabel);
            prompt.AcceptButton = confirmation;

            if (prompt.ShowDialog() == DialogResult.OK)
            {
                string input = textBox.Text;
                if (int.TryParse(input, out int newTableNumber) && newTableNumber > 0)
                {
                    try
                    {
                        using (MySqlConnection conn = Database.GetConnection())
                        {
                            if (conn.State == ConnectionState.Closed) conn.Open();

                            string query = "UPDATE froshtn SET table_cabin = @newTbl WHERE table_cabin = @oldTbl";
                            using (MySqlCommand cmd = new MySqlCommand(query, conn))
                            {
                                cmd.Parameters.AddWithValue("@newTbl", newTableNumber.ToString(enCulture));
                                cmd.Parameters.AddWithValue("@oldTbl", tableNumber.ToString(enCulture));
                                cmd.ExecuteNonQuery();
                            }
                        }

                        this.tableNumber = newTableNumber;
                        lblTableNumber.Text = tableNumber.ToString(enCulture);
                    }
                    catch { }
                }
            }
        }

        private void btnExit_Click(object sender, EventArgs e)
        {
            this.Close();
        }

        private void lblLogo_Click(object sender, EventArgs e) { }
        private void flowMenuPanel_Paint(object sender, PaintEventArgs e) { }
    }
}
